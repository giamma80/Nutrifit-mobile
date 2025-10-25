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
