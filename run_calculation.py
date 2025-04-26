import sys
import json
from check_api import calculate_carbon_footprint

if __name__ == "__main__":
    input_data = json.loads(sys.stdin.read())

    result = calculate_carbon_footprint(
        activities=input_data["activities"],
        api_key=input_data["api_key"]
    )

    print(json.dumps(result))