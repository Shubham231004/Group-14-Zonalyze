from app.ml.predictor import get_predictor
from app.ml.scenario_feature_builder import build_prediction_features


def main():
    features = build_prediction_features(
        municipality_name="Kitchener",
        business_subcategory="Indian Grocery Store",
        radius_km=5,
    )

    predictor = get_predictor()
    result = predictor.predict(features)

    print("Input features:")
    for key, value in features.items():
        print(f"{key}: {value}")

    print("\nPrediction result:")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()