import pytest
import os
from typing import Any, Dict
from httpx import AsyncClient, Response


def _minify(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_debug_image_url_in_repository(client: AsyncClient) -> None:
    """Debug test to see what's happening with image_url in repository."""
    # Domain V2 is always active
    os.environ["MEAL_DOMAIN_V2"] = "true"

    # Reset integration service
    from domain.meal.integration import _reset_integration_service

    _reset_integration_service()

    test_image_url = "https://example.com/debug-test.jpg"

    # Create meal with image
    create_mutation = _minify(
        f"""
        mutation {{
            logMeal(input: {{
                name: "Debug Meal",
                quantityG: 100,
                photoUrl: "{test_image_url}"
            }}) {{
                id
                imageUrl
            }}
        }}
        """
    )

    create_resp: Response = await client.post("/graphql", json={"query": create_mutation})
    create_data: Dict[str, Any] = create_resp.json()["data"]["logMeal"]
    created_meal_id = create_data["id"]

    print(f"Created meal ID: {created_meal_id}")
    print(f"logMeal returned imageUrl: {create_data['imageUrl']}")

    # Now let's check what's in the repository directly
    from repository.meals import meal_repo

    # Get the record directly from repository
    record = meal_repo.get(created_meal_id)
    if record:
        print(f"Repository record image_url: {record.image_url}")
        # Since MealRecord uses slots=True, it doesn't have __dict__
        # Let's print the relevant fields instead
        print(
            f"Repository record: id={record.id}, name={record.name}, image_url={record.image_url}"
        )
    else:
        print("Record not found in repository!")

    # Also list all records to see what we have
    all_records = meal_repo.list_all("00001")  # default user
    print(f"Total records in repo: {len(all_records)}")
    for r in all_records:
        if r.id == created_meal_id:
            print(f"Found our record - image_url: {r.image_url}")

    assert create_data["imageUrl"] == test_image_url
