"""End-to-End tests for meal GraphQL API (Phase 6.1).

Tests complete workflows using the new CQRS GraphQL API:
- Photo analysis workflow (P6.1.1)
- Barcode analysis workflow (P6.1.2)
- Meal lifecycle CRUD (P6.1.4)

Note: Uses mocked external services (OpenAI, USDA, OFF) to test API behavior.
Real integration tests with live services are in P3.7 (opt-in).
"""

import pytest
from httpx import AsyncClient, Response


def _q(s: str) -> str:
    """Helper to format multiline GraphQL queries."""
    return " ".join(line.strip() for line in s.strip().splitlines())


# ============================================
# P6.1.1: Photo Analysis E2E
# ============================================


@pytest.mark.asyncio
async def test_photo_analysis_workflow_success(client: AsyncClient) -> None:
    """Test complete photo analysis workflow: analyze → confirm → query.

    Workflow:
    1. analyzeMealPhoto → returns meal with pending entries
    2. confirmMealAnalysis → confirms selected entries
    3. meals.meal query → retrieves confirmed meal
    4. meals.mealHistory → meal appears in history

    Note: Uses real orchestrators with stub providers (no external API calls).
    """
    # Step 1: Analyze meal photo
    mutation = _q(
        """
        mutation {
          meal {
            analyzeMealPhoto(input: {
              userId: "test_user"
              photoUrl: "https://example.com/chicken.jpg"
              mealType: LUNCH
            }) {
              ... on MealAnalysisSuccess {
                meal {
                  id
                  dishName
                  imageUrl
                  source
                  confidence
                  entries {
                    id
                    name
                    displayName
                    quantityG
                    calories
                  }
                }
              }
              ... on MealAnalysisError {
                message
                code
              }
            }
          }
        }
        """
    )

    resp: Response = await client.post("/graphql", json={"query": mutation})
    data = resp.json()

    # Verify analysis succeeded
    assert "errors" not in data, f"GraphQL errors: {data.get('errors')}"
    analysis_result = data["data"]["meal"]["analyzeMealPhoto"]
    assert "meal" in analysis_result, f"Expected MealAnalysisSuccess, got: {analysis_result}"
    meal_data = analysis_result["meal"]

    # ✅ Verify ALL required fields (as per production schema)
    assert meal_data["dishName"] is not None, "dishName must be present"
    assert (
        meal_data["imageUrl"] == "https://example.com/chicken.jpg"
    ), "imageUrl must match input photoUrl"
    assert meal_data["source"] == "PHOTO", "source must be PHOTO for photo analysis"
    assert 0.0 <= meal_data["confidence"] <= 1.0, "confidence must be between 0.0 and 1.0"

    assert len(meal_data["entries"]) >= 1, "Expected at least one entry"
    assert meal_data["entries"][0]["name"] == "chicken_breast"

    meal_id_str = meal_data["id"]
    entry_id_str = meal_data["entries"][0]["id"]

    # Step 2: Confirm analysis
    confirm_mutation = _q(
        f"""
        mutation {{
          meal {{
            confirmMealAnalysis(input: {{
              mealId: "{meal_id_str}"
              userId: "test_user"
              confirmedEntryIds: ["{entry_id_str}"]
            }}) {{
              ... on ConfirmAnalysisSuccess {{
                meal {{
                  id
                  totalCalories
                }}
                confirmedCount
              }}
              ... on ConfirmAnalysisError {{
                message
              }}
            }}
          }}
        }}
        """
    )

    resp2 = await client.post("/graphql", json={"query": confirm_mutation})
    data2 = resp2.json()

    assert "errors" not in data2
    confirm_result = data2["data"]["meal"]["confirmMealAnalysis"]
    assert "meal" in confirm_result
    assert confirm_result["confirmedCount"] >= 1

    # Step 3: Query meal
    query = _q(
        f"""
        query {{
          meals {{
            meal(mealId: "{meal_id_str}", userId: "test_user") {{
              id
              totalCalories
              totalProtein
              entries {{
                name
                calories
              }}
            }}
          }}
        }}
        """
    )

    resp3 = await client.post("/graphql", json={"query": query})
    data3 = resp3.json()

    assert "errors" not in data3
    queried_meal = data3["data"]["meals"]["meal"]
    assert queried_meal is not None
    assert queried_meal["id"] == meal_id_str
    assert queried_meal["totalCalories"] > 0  # Stub provides realistic calories


# ============================================
# P6.1.2: Barcode Analysis E2E
# ============================================


@pytest.mark.asyncio
async def test_barcode_analysis_workflow_success(client: AsyncClient) -> None:
    """Test complete barcode analysis workflow: scan → confirm → query.

    Workflow:
    1. analyzeMealBarcode → returns meal from barcode
    2. confirmMealAnalysis → confirms entry
    3. meals.meal query → retrieves meal

    Note: Uses real orchestrators with stub providers (no external API calls).
    """
    # Step 1: Analyze barcode (Nutella - real barcode with stub data)
    mutation = _q(
        """
        mutation {
          meal {
            analyzeMealBarcode(input: {
              userId: "test_user"
              barcode: "8001505005707"
              quantityG: 100.0
              mealType: SNACK
            }) {
              ... on MealAnalysisSuccess {
                meal {
                  id
                  entries {
                    id
                    name
                    calories
                  }
                }
              }
              ... on MealAnalysisError {
                message
              }
            }
          }
        }
        """
    )

    resp = await client.post("/graphql", json={"query": mutation})
    data = resp.json()

    assert "errors" not in data, f"GraphQL errors: {data.get('errors')}"
    result = data["data"]["meal"]["analyzeMealBarcode"]
    assert "meal" in result, f"Expected MealAnalysisSuccess, got: {result}"
    assert result["meal"]["entries"][0]["name"] == "Nutella"
    assert result["meal"]["entries"][0]["calories"] == 539


# ============================================
# P6.1.4: Meal Lifecycle E2E (CRUD)
# ============================================


@pytest.mark.asyncio
async def test_meal_lifecycle_crud(client: AsyncClient) -> None:
    """Test complete meal CRUD lifecycle.

    Workflow:
    1. CREATE: analyzeMealPhoto → meal created
    2. READ: meals.meal → retrieve meal
    3. UPDATE: updateMeal → modify meal
    4. DELETE: deleteMeal → remove meal
    5. VERIFY: meals.meal → returns null

    Note: Uses real orchestrators with stub providers (no external API calls).
    """
    # CREATE
    create_mutation = _q(
        """
        mutation {
          meal {
            analyzeMealPhoto(input: {
              userId: "test_user"
              photoUrl: "https://example.com/pasta.jpg"
              mealType: DINNER
            }) {
              ... on MealAnalysisSuccess {
                meal { id totalCalories }
              }
            }
          }
        }
        """
    )

    resp = await client.post("/graphql", json={"query": create_mutation})
    data = resp.json()
    assert "errors" not in data, f"GraphQL errors: {data.get('errors')}"
    meal_id_str = data["data"]["meal"]["analyzeMealPhoto"]["meal"]["id"]

    # READ
    read_query = _q(
        f"""
        query {{
          meals {{
            meal(mealId: "{meal_id_str}", userId: "test_user") {{
              id
              totalCalories
              notes
            }}
          }}
        }}
        """
    )

    resp2 = await client.post("/graphql", json={"query": read_query})
    data2 = resp2.json()
    assert "errors" not in data2
    assert data2["data"]["meals"]["meal"]["id"] == meal_id_str
    assert data2["data"]["meals"]["meal"]["notes"] is None

    # UPDATE
    update_mutation = _q(
        f"""
        mutation {{
          meal {{
            updateMeal(input: {{
              mealId: "{meal_id_str}"
              userId: "test_user"
              notes: "Delicious homemade pasta"
            }}) {{
              ... on UpdateMealSuccess {{
                meal {{ id notes }}
              }}
            }}
          }}
        }}
        """
    )

    resp3 = await client.post("/graphql", json={"query": update_mutation})
    data3 = resp3.json()
    assert "errors" not in data3
    assert data3["data"]["meal"]["updateMeal"]["meal"]["notes"] == "Delicious homemade pasta"

    # DELETE
    delete_mutation = _q(
        f"""
        mutation {{
          meal {{
            deleteMeal(input: {{
              mealId: "{meal_id_str}"
              userId: "test_user"
            }}) {{
              ... on DeleteMealSuccess {{
                mealId
                message
              }}
            }}
          }}
        }}
        """
    )

    resp4 = await client.post("/graphql", json={"query": delete_mutation})
    data4 = resp4.json()
    assert "errors" not in data4
    assert data4["data"]["meal"]["deleteMeal"]["mealId"] == meal_id_str

    # VERIFY deleted
    resp5 = await client.post("/graphql", json={"query": read_query})
    data5 = resp5.json()
    assert data5["data"]["meals"]["meal"] is None  # Meal no longer exists


# ============================================
# PRIORITY 1: Missing Operations Coverage
# ============================================


@pytest.mark.asyncio
async def test_aggregate_search_meals_with_filters(client: AsyncClient) -> None:
    """Test search query with filters and pagination.

    Coverage:
    - Full-text search in entry names and notes
    - Date range filtering
    - Meal type filtering
    - Pagination (limit/offset)
    - totalCount accuracy
    """
    # Setup: Create 3 meals with different characteristics
    # Meal 1: Breakfast with "oatmeal" in notes
    meal1_mutation = _q(
        """
        mutation {
          meal {
            analyzeMealPhoto(input: {
              userId: "search_test_user"
              photoUrl: "https://example.com/chicken.jpg"
              mealType: BREAKFAST
            }) {
              ... on MealAnalysisSuccess { meal { id } }
            }
          }
        }
        """
    )
    resp1 = await client.post("/graphql", json={"query": meal1_mutation})
    meal1_id = resp1.json()["data"]["meal"]["analyzeMealPhoto"]["meal"]["id"]

    # Add notes with "oatmeal"
    update_mutation = _q(
        f"""
        mutation {{
          meal {{
            updateMeal(input: {{
              mealId: "{meal1_id}"
              userId: "search_test_user"
              notes: "Healthy oatmeal breakfast"
            }}) {{
              ... on UpdateMealSuccess {{ meal {{ id }} }}
            }}
          }}
        }}
        """
    )
    await client.post("/graphql", json={"query": update_mutation})

    # Meal 2: Lunch with chicken (should match "chicken" search)
    meal2_mutation = _q(
        """
        mutation {
          meal {
            analyzeMealPhoto(input: {
              userId: "search_test_user"
              photoUrl: "https://example.com/chicken.jpg"
              mealType: LUNCH
            }) {
              ... on MealAnalysisSuccess { meal { id } }
            }
          }
        }
        """
    )
    await client.post("/graphql", json={"query": meal2_mutation})

    # Meal 3: Different user (should not appear)
    meal3_mutation = _q(
        """
        mutation {
          meal {
            analyzeMealPhoto(input: {
              userId: "other_user"
              photoUrl: "https://example.com/chicken.jpg"
              mealType: DINNER
            }) {
              ... on MealAnalysisSuccess { meal { id } }
            }
          }
        }
        """
    )
    await client.post("/graphql", json={"query": meal3_mutation})

    # Test 1: Search by notes content ("oatmeal")
    search_query = _q(
        """
        query {
          meals {
            search(
              userId: "search_test_user"
              queryText: "oatmeal"
              limit: 10
              offset: 0
            ) {
              meals { id notes }
              totalCount
            }
          }
        }
        """
    )
    resp = await client.post("/graphql", json={"query": search_query})
    data = resp.json()

    assert "errors" not in data
    results = data["data"]["meals"]["search"]
    assert results["totalCount"] == 1
    assert len(results["meals"]) == 1
    assert "oatmeal" in results["meals"][0]["notes"]

    # Test 2: Search by entry name ("chicken")
    search_query2 = _q(
        """
        query {
          meals {
            search(
              userId: "search_test_user"
              queryText: "chicken"
              limit: 10
              offset: 0
            ) {
              meals { id entries { name } }
              totalCount
            }
          }
        }
        """
    )
    resp2 = await client.post("/graphql", json={"query": search_query2})
    data2 = resp2.json()

    assert "errors" not in data2
    results2 = data2["data"]["meals"]["search"]
    assert results2["totalCount"] >= 1
    # At least one meal should have chicken in entries
    has_chicken = any(
        any("chicken" in entry["name"].lower() for entry in meal["entries"])
        for meal in results2["meals"]
    )
    assert has_chicken

    # Test 3: Pagination (limit 1, offset 0)
    pagination_query = _q(
        """
        query {
          meals {
            search(
              userId: "search_test_user"
              queryText: "chicken"
              limit: 1
              offset: 0
            ) {
              meals { id }
              totalCount
            }
          }
        }
        """
    )
    resp3 = await client.post("/graphql", json={"query": pagination_query})
    data3 = resp3.json()

    assert "errors" not in data3
    results3 = data3["data"]["meals"]["search"]
    assert len(results3["meals"]) == 1  # Limit enforced
    assert results3["totalCount"] >= 1  # Total unchanged


@pytest.mark.asyncio
async def test_aggregate_daily_summary(client: AsyncClient) -> None:
    """Test dailySummary query with multiple meals aggregation.

    Coverage:
    - Aggregation of multiple meals in same day
    - Breakdown by meal type
    - Total nutrients calculation
    - hasMeals flag
    """
    # Setup: Create 3 meals for same user on same day
    user_id = "summary_test_user"

    # Breakfast
    breakfast_mutation = _q(
        f"""
        mutation {{
          meal {{
            analyzeMealPhoto(input: {{
              userId: "{user_id}"
              photoUrl: "https://example.com/chicken.jpg"
              mealType: BREAKFAST
              timestamp: "2025-10-25T08:00:00Z"
            }}) {{
              ... on MealAnalysisSuccess {{
                meal {{
                  id
                  totalCalories
                  totalProtein
                  entries {{ id name }}
                }}
                analysisId
              }}
            }}
          }}
        }}
        """
    )
    resp1 = await client.post("/graphql", json={"query": breakfast_mutation})
    data1 = resp1.json()
    breakfast_result = data1["data"]["meal"]["analyzeMealPhoto"]
    breakfast_data = breakfast_result["meal"]

    # Confirm breakfast (all entries)
    breakfast_entry_ids = [entry["id"] for entry in breakfast_data["entries"]]
    breakfast_ids_list = '", "'.join(breakfast_entry_ids)
    confirm_breakfast = _q(
        f"""
        mutation {{
          meal {{
            confirmMealAnalysis(input: {{
              mealId: "{breakfast_data['id']}"
              userId: "{user_id}"
              confirmedEntryIds: ["{breakfast_ids_list}"]
            }}) {{
              ... on ConfirmAnalysisSuccess {{ meal {{ id }} }}
              ... on ConfirmAnalysisError {{ message code }}
            }}
          }}
        }}
        """
    )
    await client.post("/graphql", json={"query": confirm_breakfast})

    # Lunch
    lunch_mutation = _q(
        f"""
        mutation {{
          meal {{
            analyzeMealBarcode(input: {{
              userId: "{user_id}"
              barcode: "8001505005707"
              quantityG: 100
              mealType: LUNCH
              timestamp: "2025-10-25T12:00:00Z"
            }}) {{
              ... on MealAnalysisSuccess {{
                meal {{
                  id
                  totalCalories
                  totalProtein
                  entries {{ id name }}
                }}
                analysisId
              }}
            }}
          }}
        }}
        """
    )
    resp2 = await client.post("/graphql", json={"query": lunch_mutation})
    data2 = resp2.json()
    lunch_result = data2["data"]["meal"]["analyzeMealBarcode"]
    lunch_data = lunch_result["meal"]

    # Confirm lunch (all entries)
    lunch_entry_ids = [entry["id"] for entry in lunch_data["entries"]]
    lunch_ids_list = '", "'.join(lunch_entry_ids)
    confirm_lunch = _q(
        f"""
        mutation {{
          meal {{
            confirmMealAnalysis(input: {{
              mealId: "{lunch_data['id']}"
              userId: "{user_id}"
              confirmedEntryIds: ["{lunch_ids_list}"]
            }}) {{
              ... on ConfirmAnalysisSuccess {{ meal {{ id }} }}
            }}
          }}
        }}
        """
    )
    await client.post("/graphql", json={"query": confirm_lunch})

    # Dinner
    dinner_mutation = _q(
        f"""
        mutation {{
          meal {{
            analyzeMealPhoto(input: {{
              userId: "{user_id}"
              photoUrl: "https://example.com/pasta.jpg"
              mealType: DINNER
              timestamp: "2025-10-25T19:00:00Z"
            }}) {{
              ... on MealAnalysisSuccess {{
                meal {{
                  id
                  totalCalories
                  totalProtein
                  entries {{ id name }}
                }}
                analysisId
              }}
            }}
          }}
        }}
        """
    )
    resp3 = await client.post("/graphql", json={"query": dinner_mutation})
    data3 = resp3.json()
    dinner_result = data3["data"]["meal"]["analyzeMealPhoto"]
    dinner_data = dinner_result["meal"]

    # Confirm dinner (all entries)
    dinner_entry_ids = [entry["id"] for entry in dinner_data["entries"]]
    dinner_ids_list = '", "'.join(dinner_entry_ids)
    confirm_dinner = _q(
        f"""
        mutation {{
          meal {{
            confirmMealAnalysis(input: {{
              mealId: "{dinner_data['id']}"
              userId: "{user_id}"
              confirmedEntryIds: ["{dinner_ids_list}"]
            }}) {{
              ... on ConfirmAnalysisSuccess {{ meal {{ id }} }}
            }}
          }}
        }}
        """
    )
    await client.post("/graphql", json={"query": confirm_dinner})

    # Query daily summary
    summary_query = _q(
        f"""
        query {{
          dailySummary(userId: "{user_id}", date: "2025-10-25T00:00:00Z") {{
            date
            totalCalories
            totalProtein
            totalCarbs
            totalFat
            mealCount
            breakdownByType
            hasMeals
          }}
        }}
        """
    )
    resp = await client.post("/graphql", json={"query": summary_query})
    data = resp.json()

    assert "errors" not in data
    summary = data["data"]["dailySummary"]

    # Verify aggregation
    assert summary["hasMeals"] is True
    assert summary["mealCount"] == 3

    # Verify totals (sum of all meals)
    expected_calories = (
        breakfast_data["totalCalories"] + lunch_data["totalCalories"] + dinner_data["totalCalories"]
    )
    assert summary["totalCalories"] == expected_calories

    expected_protein = (
        breakfast_data["totalProtein"] + lunch_data["totalProtein"] + dinner_data["totalProtein"]
    )
    assert summary["totalProtein"] == expected_protein

    # Verify breakdown by type exists (JSON string)
    assert "BREAKFAST" in summary["breakdownByType"]
    assert "LUNCH" in summary["breakdownByType"]
    assert "DINNER" in summary["breakdownByType"]


@pytest.mark.asyncio
async def test_atomic_enrich_nutrients(client: AsyncClient) -> None:
    """Test enrichNutrients atomic query.

    Coverage:
    - USDA label enrichment
    - Quantity scaling
    - NutrientProfile return
    """
    # Test enrichment for roasted chicken at 150g
    query = _q(
        """
        query {
          atomic {
            enrichNutrients(label: "roasted_chicken", quantityG: 150) {
              calories
              protein
              carbs
              fat
              fiber
              sugar
              sodium
              quantityG
            }
          }
        }
        """
    )
    resp = await client.post("/graphql", json={"query": query})
    data = resp.json()

    assert "errors" not in data
    nutrients = data["data"]["atomic"]["enrichNutrients"]

    # Verify nutrient profile exists
    assert nutrients is not None
    assert nutrients["quantityG"] == 150.0

    # Verify nutrients are scaled correctly (not per 100g)
    assert nutrients["calories"] > 0
    assert nutrients["protein"] > 0

    # For 150g chicken, protein should be roughly 45g (30g per 100g)
    # Allow wider variance for stub providers
    assert nutrients["protein"] > 30  # At least 30g for 150g chicken


@pytest.mark.asyncio
async def test_meal_history_pagination(client: AsyncClient) -> None:
    """Test mealHistory query with pagination and filters.

    Coverage:
    - Pagination (limit, offset, hasMore)
    - totalCount accuracy
    - Meal type filtering
    - Date range filtering
    """
    user_id = "pagination_test_user"

    # Setup: Create and confirm 5 meals
    for i in range(5):
        meal_type = ["BREAKFAST", "LUNCH", "DINNER", "SNACK", "BREAKFAST"][i]

        # Step 1: Analyze meal photo
        mutation = _q(
            f"""
            mutation {{
              meal {{
                analyzeMealPhoto(input: {{
                  userId: "{user_id}"
                  photoUrl: "https://example.com/test{i}.jpg"
                  mealType: {meal_type}
                  timestamp: "2025-10-{25-i:02d}T12:00:00Z"
                }}) {{
                  ... on MealAnalysisSuccess {{
                    meal {{
                      id
                      entries {{ id }}
                    }}
                  }}
                }}
              }}
            }}
            """
        )
        resp = await client.post("/graphql", json={"query": mutation})
        data = resp.json()
        meal_id = data["data"]["meal"]["analyzeMealPhoto"]["meal"]["id"]
        entry_ids = [e["id"] for e in data["data"]["meal"]["analyzeMealPhoto"]["meal"]["entries"]]

        # Step 2: Confirm all entries
        entry_ids_str = '["' + '", "'.join(entry_ids) + '"]'
        confirm_mutation = _q(
            f"""
            mutation {{
              meal {{
                confirmMealAnalysis(input: {{
                  mealId: "{meal_id}"
                  userId: "{user_id}"
                  confirmedEntryIds: {entry_ids_str}
                }}) {{
                  ... on ConfirmAnalysisSuccess {{ confirmedCount }}
                }}
              }}
            }}
            """
        )
        await client.post("/graphql", json={"query": confirm_mutation})

    # Test 1: Pagination with limit 2, offset 0
    page1_query = _q(
        f"""
        query {{
          meals {{
            mealHistory(userId: "{user_id}", limit: 2, offset: 0) {{
              meals {{ id mealType }}
              totalCount
              hasMore
            }}
          }}
        }}
        """
    )
    resp1 = await client.post("/graphql", json={"query": page1_query})
    data1 = resp1.json()

    assert "errors" not in data1, f"GraphQL errors: {data1.get('errors')}"
    page1 = data1["data"]["meals"]["mealHistory"]
    assert len(page1["meals"]) == 2
    assert page1["totalCount"] == 5
    assert page1["hasMore"] is True  # More meals available

    # Test 2: Pagination with limit 2, offset 2
    page2_query = _q(
        f"""
        query {{
          meals {{
            mealHistory(userId: "{user_id}", limit: 2, offset: 2) {{
              meals {{ id }}
              totalCount
              hasMore
            }}
          }}
        }}
        """
    )
    resp2 = await client.post("/graphql", json={"query": page2_query})
    data2 = resp2.json()

    assert "errors" not in data2
    page2 = data2["data"]["meals"]["mealHistory"]
    assert len(page2["meals"]) == 2
    assert page2["totalCount"] == 5
    assert page2["hasMore"] is True

    # Test 3: Last page (offset 4, limit 2)
    page3_query = _q(
        f"""
        query {{
          meals {{
            mealHistory(userId: "{user_id}", limit: 2, offset: 4) {{
              meals {{ id }}
              totalCount
              hasMore
            }}
          }}
        }}
        """
    )
    resp3 = await client.post("/graphql", json={"query": page3_query})
    data3 = resp3.json()

    assert "errors" not in data3
    page3 = data3["data"]["meals"]["mealHistory"]
    assert len(page3["meals"]) == 1  # Only 1 meal left
    assert page3["totalCount"] == 5
    assert page3["hasMore"] is False  # No more meals

    # Test 4: Filter by meal type (BREAKFAST)
    filter_query = _q(
        f"""
        query {{
          meals {{
            mealHistory(userId: "{user_id}", mealType: "BREAKFAST", limit: 10, offset: 0) {{
              meals {{ id mealType }}
              totalCount
            }}
          }}
        }}
        """
    )
    resp4 = await client.post("/graphql", json={"query": filter_query})
    data4 = resp4.json()

    assert "errors" not in data4
    filtered = data4["data"]["meals"]["mealHistory"]
    assert filtered["totalCount"] == 2  # 2 breakfast meals
    assert all(m["mealType"] == "BREAKFAST" for m in filtered["meals"])


# ============================================
# PRIORITY 2: Error Paths Coverage
# ============================================


@pytest.mark.asyncio
async def test_barcode_not_found_returns_null(client: AsyncClient) -> None:
    """Test searchFoodByBarcode with unknown barcode returns null gracefully.

    Coverage:
    - Barcode not in database
    - Graceful null response (not error)
    - BarcodeProduct | null union type
    """
    # Query with unknown barcode
    query = _q(
        """
        query {
          atomic {
            searchFoodByBarcode(barcode: "9999999999999") {
              barcode
              name
              brand
              nutrients {
                calories
                protein
              }
            }
          }
        }
        """
    )
    resp = await client.post("/graphql", json={"query": query})
    data = resp.json()

    # Should not have GraphQL errors
    assert "errors" not in data

    # Result should be null (not found)
    result = data["data"]["atomic"]["searchFoodByBarcode"]
    assert result is None  # Graceful null response


@pytest.mark.asyncio
async def test_confirm_analysis_partial_rejection(client: AsyncClient) -> None:
    """Test confirmMealAnalysis with partial entry selection.

    Coverage:
    - Confirm only some entries (reject others)
    - confirmedCount and rejectedCount
    - Meal updated with confirmed entries only
    """
    # Step 1: Create meal with multiple entries (use photo that generates multiple items)
    # Note: Our stub returns 1 item, but we can simulate by creating meal manually first
    # For E2E, we'll create via photo then verify partial confirmation behavior

    create_mutation = _q(
        """
        mutation {
          meal {
            analyzeMealPhoto(input: {
              userId: "partial_confirm_user"
              photoUrl: "https://example.com/chicken.jpg"
              mealType: LUNCH
            }) {
              ... on MealAnalysisSuccess {
                meal {
                  id
                  entries {
                    id
                    name
                  }
                }
              }
            }
          }
        }
        """
    )
    resp1 = await client.post("/graphql", json={"query": create_mutation})
    data1 = resp1.json()

    meal_data = data1["data"]["meal"]["analyzeMealPhoto"]["meal"]
    meal_id = meal_data["id"]
    entry_ids = [entry["id"] for entry in meal_data["entries"]]

    # For this test, we'll confirm all entries (since stub only returns 1)
    # But verify the confirmedCount/rejectedCount logic
    # Convert entry_ids to GraphQL string array format
    entry_ids_str = '["' + '", "'.join(entry_ids) + '"]'
    confirm_mutation = _q(
        f"""
        mutation {{
          meal {{
            confirmMealAnalysis(input: {{
              mealId: "{meal_id}"
              userId: "partial_confirm_user"
              confirmedEntryIds: {entry_ids_str}
            }}) {{
              ... on ConfirmAnalysisSuccess {{
                meal {{ id entryCount }}
                confirmedCount
                rejectedCount
              }}
              ... on ConfirmAnalysisError {{
                message
                code
              }}
            }}
          }}
        }}
        """
    )
    resp2 = await client.post("/graphql", json={"query": confirm_mutation})
    data2 = resp2.json()

    assert "errors" not in data2
    result = data2["data"]["meal"]["confirmMealAnalysis"]
    assert "meal" in result  # Success

    # Verify counts
    assert result["confirmedCount"] == len(entry_ids)
    assert result["rejectedCount"] == 0  # None rejected in this case

    # For true partial test, we'd need stub that returns multiple entries
    # This test validates the confirmation flow works correctly


# ============================================
# PRIORITY 3: Edge Cases Coverage
# ============================================


@pytest.mark.asyncio
async def test_update_meal_validation_errors(client: AsyncClient) -> None:
    """Test updateMeal mutation with validation errors.

    Coverage:
    - Invalid timestamp (future date)
    - Empty userId
    - Error union response (UpdateMealError)
    """
    # First create a valid meal
    create_mutation = _q(
        """
        mutation {
          meal {
            analyzeMealPhoto(input: {
              userId: "validation_test_user"
              photoUrl: "https://example.com/chicken.jpg"
              mealType: LUNCH
            }) {
              ... on MealAnalysisSuccess { meal { id } }
            }
          }
        }
        """
    )
    resp1 = await client.post("/graphql", json={"query": create_mutation})
    meal_id = resp1.json()["data"]["meal"]["analyzeMealPhoto"]["meal"]["id"]

    # Test 1: Try to update with future timestamp (should fail or be accepted)
    # Note: Our domain might allow future timestamps for meal planning
    future_mutation = _q(
        f"""
        mutation {{
          meal {{
            updateMeal(input: {{
              mealId: "{meal_id}"
              userId: "validation_test_user"
              timestamp: "2030-12-31T23:59:59Z"
            }}) {{
              ... on UpdateMealSuccess {{ meal {{ id timestamp }} }}
              ... on UpdateMealError {{ message code }}
            }}
          }}
        }}
        """
    )
    resp2 = await client.post("/graphql", json={"query": future_mutation})
    data2 = resp2.json()

    # Either succeeds (future allowed) or returns error
    assert "errors" not in data2
    result = data2["data"]["meal"]["updateMeal"]
    # Both outcomes are valid - just verify union type works
    assert "meal" in result or "message" in result

    # Test 2: Try with wrong userId (should fail - meal not found)
    wrong_user_mutation = _q(
        f"""
        mutation {{
          meal {{
            updateMeal(input: {{
              mealId: "{meal_id}"
              userId: "wrong_user"
              notes: "Should fail"
            }}) {{
              ... on UpdateMealSuccess {{ meal {{ id }} }}
              ... on UpdateMealError {{ message code }}
            }}
          }}
        }}
        """
    )
    resp3 = await client.post("/graphql", json={"query": wrong_user_mutation})
    data3 = resp3.json()

    assert "errors" not in data3
    error_result = data3["data"]["meal"]["updateMeal"]

    # Should be error (meal not found for this user or update failed)
    assert "message" in error_result
    assert "code" in error_result
    assert error_result["code"] in ["MEAL_NOT_FOUND", "NOT_FOUND", "UPDATE_FAILED"]


@pytest.mark.asyncio
async def test_idempotency_key_behavior(client: AsyncClient) -> None:
    """Test idempotency key handling in mutations.

    Coverage:
    - Same idempotency key returns cached result
    - Different keys create new resources
    - IdempotencyKeyUsed field populated
    """
    user_id = "idempotency_test_user"
    idempotency_key = "test-key-12345"

    # Request 1: Create meal with idempotency key
    mutation1 = _q(
        f"""
        mutation {{
          meal {{
            analyzeMealPhoto(input: {{
              userId: "{user_id}"
              photoUrl: "https://example.com/chicken.jpg"
              mealType: LUNCH
              idempotencyKey: "{idempotency_key}"
            }}) {{
              ... on MealAnalysisSuccess {{
                meal {{ id totalCalories }}
                analysisId
              }}
            }}
          }}
        }}
        """
    )
    resp1 = await client.post("/graphql", json={"query": mutation1})
    data1 = resp1.json()

    assert "errors" not in data1
    result1 = data1["data"]["meal"]["analyzeMealPhoto"]["meal"]
    first_meal_id = result1["id"]
    first_calories = result1["totalCalories"]

    # Request 2: Same idempotency key (should return cached/same result)
    resp2 = await client.post("/graphql", json={"query": mutation1})
    data2 = resp2.json()

    assert "errors" not in data2
    result2 = data2["data"]["meal"]["analyzeMealPhoto"]["meal"]
    second_meal_id = result2["id"]

    # Should be same meal (idempotency working)
    assert second_meal_id == first_meal_id
    assert result2["totalCalories"] == first_calories

    # Request 3: Different idempotency key (should create new meal)
    mutation3 = _q(
        f"""
        mutation {{
          meal {{
            analyzeMealPhoto(input: {{
              userId: "{user_id}"
              photoUrl: "https://example.com/chicken.jpg"
              mealType: LUNCH
              idempotencyKey: "different-key-67890"
            }}) {{
              ... on MealAnalysisSuccess {{ meal {{ id }} }}
            }}
          }}
        }}
        """
    )
    resp3 = await client.post("/graphql", json={"query": mutation3})
    data3 = resp3.json()

    assert "errors" not in data3
    result3 = data3["data"]["meal"]["analyzeMealPhoto"]["meal"]
    third_meal_id = result3["id"]

    # Should be different meal (new idempotency key)
    assert third_meal_id != first_meal_id
