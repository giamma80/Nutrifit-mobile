#!/bin/bash
set -e

echo "🧪 Testing 3 specific failing tests..."

echo "1️⃣ Testing gpt4v source fix..."
python -m pytest tests/test_ai_meal_photo_gpt4v_e2e.py::test_analyze_meal_photo_gpt4v_total_calories -v --tb=no -q 

echo "2️⃣ Testing USDA prompt fix..."
python -m pytest tests/test_improved_usda_labels.py::test_improved_usda_labels -v --tb=no -q

echo "3️⃣ Testing calorie correction with USDA disabled..."
AI_USDA_API_KEY="" python -m pytest tests/test_ai_meal_photo_normalization.py::test_calorie_corrected_true_case -v --tb=no -q

echo "✅ All 3 fixed tests completed!"