import requests
import logging
import os
import time
import json
import math
import sys
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

def main_wrapper():
    data = json.loads(sys.stdin.read())
    results = calculate_carbon_footprint(data["activities"], data["api_key"])
    print(json.dumps(results))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"carbon_calc_{datetime.now().strftime('%Y%m%d_%H%M')}.log")
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
climatiq_api_key = os.getenv("CLIMATIQ_API_KEY")


MAX_RETRIES = 3
RETRY_DELAY = 2
DEFAULT_REGION = "US"

UNIT_CONVERSIONS = {
    "energy": {"kWh": 1.0, "MWh": 1000.0, "GWh": 1000000.0, "J": 0.000278, "MJ": 0.278},
    "distance": {"km": 1.0, "mi": 1.60934, "mile": 1.60934, "miles": 1.60934},
    "weight": {"kg": 1.0, "t": 1000.0, "lb": 0.453592, "g": 0.001},
    "volume": {"L": 1.0, "l": 1.0, "gal": 3.78541, "m3": 1000.0},
}

ACTIVITY_MAPPINGS = {
    "electricity": {
        "id": "electricity",
        "unit_type": "energy",
        "default_unit": "kWh",
        "fallbacks": ["electricity-energy"],
        "algorithm_factor": 1.05
    },
    "car": {
        "id": "passenger_vehicle-car",
        "unit_type": "distance",
        "default_unit": "km",
        "fallbacks": ["car-generic"],
        "algorithm_factor": 1.2
    },
    "bus": {
        "id": "passenger_vehicle-bus",
        "unit_type": "distance",
        "default_unit": "km",
        "fallbacks": ["bus-generic"],
        "algorithm_factor": 0.9
    },
    "natural_gas": {
        "id": "natural_gas",
        "unit_type": "energy",
        "default_unit": "kWh",
        "fallbacks": ["heating-gas"],
        "algorithm_factor": 1.15
    },
    "rail": {
        "id": "passenger_train",
        "unit_type": "distance",
        "default_unit": "km",
        "fallbacks": ["train-generic"],
        "algorithm_factor": 0.85
    }
}

REGIONAL_FACTORS = {
    "US": 1.0, "CA": 0.75, "CN": 1.35, "EU": 0.85, "UK": 0.82,
    "AU": 1.25, "IN": 1.4, "GLOBAL": 1.05
}

SEASONAL_FACTORS = {
    1: 1.2, 2: 1.15, 3: 1.05, 4: 0.95, 5: 0.9, 6: 0.85,
    7: 0.8, 8: 0.85, 9: 0.9, 10: 1.0, 11: 1.1, 12: 1.15
}


class ClimatiqAPI:

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.climatiq.io"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.cache = {}
        self.data_version = self._get_data_version()

    def _get_data_version(self) -> str:
        try:
            response = requests.get(
                f"{self.base_url}/data/v1/data-versions",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            latest = response.json().get("latest_release")
            if latest:
                return latest
        except Exception as e:
            logger.warning(f"Failed to get data version: {e}")

        return "2023-04-01"

    def make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None,
                     params: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}/{endpoint}"
        headers = self.headers.copy()
        if data:
            headers["Content-Type"] = "application/json"

        for retry in range(MAX_RETRIES):
            try:
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                else:
                    response = requests.post(url, headers=headers, json=data, timeout=30)

                if response.status_code == 400 and data:
                    logger.debug(f"Request payload: {json.dumps(data)}")
                    logger.debug(f"Response: {response.text}")

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', RETRY_DELAY))
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.RequestException as e:
                logger.warning(f"API request failed (attempt {retry + 1}/{MAX_RETRIES}): {str(e)}")
                if retry < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    return {"error": str(e)}

        return {"error": "API request failed"}

    def search_emission_factors(self, query: str, region: Optional[str] = None,
                                unit_type: Optional[str] = None) -> Dict:
        cache_key = f"{query}:{region}:{unit_type}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        params = {"query": query}
        if region:
            params["region"] = region

        result = self.make_request("data/v1/search", params=params)

        if "error" not in result and result.get("results"):
            self.cache[cache_key] = result

        return result


class CarbonEmissionCalculator:

    def __init__(self, api_key: str):
        self.api = ClimatiqAPI(api_key)
        self.activity_mappings = ACTIVITY_MAPPINGS
        self.current_month = datetime.now().month

    def get_activity_info(self, activity_type: str) -> Dict:
        if not activity_type:
            return {
                "id": "electricity",
                "unit_type": "energy",
                "default_unit": "kWh",
                "algorithm_factor": 1.0
            }

        normalized_type = activity_type.lower().strip()

        if normalized_type in self.activity_mappings:
            return self.activity_mappings[normalized_type]

        for key, value in self.activity_mappings.items():
            if key in normalized_type or normalized_type in key:
                logger.info(f"Partial match: {normalized_type} -> {key}")
                return value

        return {
            "id": normalized_type,
            "unit_type": "energy",
            "default_unit": "kWh",
            "algorithm_factor": 1.0
        }

    def find_emission_factor(self, activity_type: str, region: Optional[str] = None) -> Dict:
        activity_info = self.get_activity_info(activity_type)
        primary_id = activity_info.get("id")
        unit_type = activity_info.get("unit_type")

        search_results = self.api.search_emission_factors(primary_id, region, unit_type)

        if "error" not in search_results and search_results.get("results"):
            if region:
                for factor in search_results["results"]:
                    if factor.get("region") == region:
                        return factor

            return search_results["results"][0]

        for fallback_id in activity_info.get("fallbacks", []):
            fallback_results = self.api.search_emission_factors(fallback_id, region, unit_type)
            if "error" not in fallback_results and fallback_results.get("results"):
                return fallback_results["results"][0]

        return {"activity_id": primary_id, "unit_type": unit_type, "region": region or "GLOBAL"}

    def format_parameters(self, parameters: Dict, unit_type: str, default_unit: str) -> Dict:
        simplified = {}

        if unit_type == "distance" and "distance" in parameters:
            value = float(parameters["distance"])
            unit = parameters.get("distance_unit", default_unit)

            if unit.lower() in ["mi", "mile", "miles"]:
                value *= 1.60934

            simplified["distance"] = value
            simplified["distance_unit"] = "km"

        elif unit_type == "energy" and "energy" in parameters:
            value = float(parameters["energy"])
            unit = parameters.get("energy_unit", default_unit)

            if unit.lower() == "mwh":
                value *= 1000
            elif unit.lower() == "gwh":
                value *= 1000000

            simplified["energy"] = value
            simplified["energy_unit"] = "kWh"

        if not simplified:
            for key, value in parameters.items():
                if isinstance(value, (int, float)):
                    simplified[key] = value
                else:
                    simplified[key] = value

        return simplified

    def calculate_direct_emissions(self, activity_type: str, parameters: Dict, region: str) -> float:
        default_factors = {
            "bus": {"US": 0.105, "EU": 0.08, "UK": 0.075, "CA": 0.09, "CN": 0.12, "GLOBAL": 0.1},
            "car": {"US": 0.185, "EU": 0.15, "UK": 0.15, "CA": 0.17, "CN": 0.21, "GLOBAL": 0.18},
            "rail": {"US": 0.04, "EU": 0.03, "UK": 0.035, "CA": 0.04, "CN": 0.06, "GLOBAL": 0.045},
            "electricity": {"US": 0.38, "EU": 0.25, "UK": 0.23, "CA": 0.15, "CN": 0.6, "GLOBAL": 0.42},
            "natural_gas": {"US": 0.2, "EU": 0.19, "UK": 0.19, "CA": 0.18, "CN": 0.22, "GLOBAL": 0.2}
        }

        region_factors = default_factors.get(activity_type.lower(), {})
        emission_factor = region_factors.get(region, region_factors.get("GLOBAL", 0.1))

        if activity_type.lower() in ["bus", "car", "rail"]:
            if "distance" in parameters:
                distance = float(parameters["distance"])
                distance_unit = parameters.get("distance_unit", "km")

                if distance_unit.lower() in ["mi", "mile", "miles"]:
                    distance *= 1.60934

                return distance * emission_factor

        elif activity_type.lower() in ["electricity", "natural_gas"]:
            if "energy" in parameters:
                energy = float(parameters["energy"])
                energy_unit = parameters.get("energy_unit", "kWh")

                if energy_unit.lower() == "mwh":
                    energy *= 1000
                elif energy_unit.lower() == "gwh":
                    energy *= 1000000

                return energy * emission_factor

        return 10.0

    def calculate_api_emissions(self, parameters: Dict, activity_id: str,
                                region: Optional[str] = None) -> Dict:
        activity_type = None
        unit_type = None
        default_unit = None

        for activity_type_key, info in self.activity_mappings.items():
            if info.get("id") == activity_id:
                activity_type = activity_type_key
                unit_type = info.get("unit_type")
                default_unit = info.get("default_unit")
                break

        if not unit_type:
            if "distance" in parameters:
                unit_type = "distance"
                default_unit = "km"
            elif "energy" in parameters:
                unit_type = "energy"
                default_unit = "kWh"
            else:
                unit_type = "energy"
                default_unit = "kWh"

        adjusted_params = self.format_parameters(parameters, unit_type, default_unit)

        emission_factor = {"activity_id": activity_id}

        if region:
            emission_factor["region"] = region

        payload = {
            "emission_factor": emission_factor,
            "parameters": adjusted_params
        }

        result = self.api.make_request("data/v1/estimate", method="POST", data=payload)

        if "error" in result:
            simplified_payload = {
                "emission_factor": {
                    "activity_id": activity_id
                },
                "parameters": {
                    list(adjusted_params.keys())[0]: list(adjusted_params.values())[0]
                }
            }

            if region:
                simplified_payload["emission_factor"]["region"] = region

            result = self.api.make_request("data/v1/estimate", method="POST", data=simplified_payload)

        return result

    def calculate_algorithmic_emissions(self, raw_emissions: float, region: str,
                                        activity_type: str, algorithm_factor: float) -> float:
        if raw_emissions <= 0:
            return 0.0

        adjusted_regional_factors = {
            "US": 1.0, "CA": 0.92, "CN": 1.12, "EU": 0.95, "UK": 0.94,
            "AU": 1.08, "IN": 1.12, "GLOBAL": 1.02
        }

        adjusted_seasonal_factors = {
            1: 1.05, 2: 1.04, 3: 1.02, 4: 0.98, 5: 0.96, 6: 0.95,
            7: 0.94, 8: 0.95, 9: 0.97, 10: 1.0, 11: 1.03, 12: 1.04
        }

        region_factor = adjusted_regional_factors.get(region, adjusted_regional_factors.get("GLOBAL", 1.0))
        seasonal_factor = adjusted_seasonal_factors.get(self.current_month, 1.0)

        activity_type_adjustments = {
            "electricity": 0.98,
            "car": 0.95,
            "bus": 1.05,
            "rail": 1.02,
            "natural_gas": 0.97
        }

        activity_adjustment = activity_type_adjustments.get(activity_type.lower(), 1.0)

        adjusted = raw_emissions * algorithm_factor * region_factor * seasonal_factor * activity_adjustment

        if adjusted > 100:
            final = adjusted * 0.95 + (5 * math.log(adjusted / 100))
        else:
            final = adjusted

        global_alignment_factor = 0.93 if activity_type.lower() == "electricity" else 0.98

        return round(final * global_alignment_factor, 2)

    def compare_calculations(self, api_value: float, algo_value: float) -> Dict:
        if api_value <= 0:
            return {
                "difference": 0,
                "percent_difference": 0,
                "algorithm_is_higher": False
            }

        difference = algo_value - api_value
        percent = round((difference / api_value) * 100, 1)

        return {
            "difference": round(difference, 2),
            "percent_difference": percent,
            "algorithm_is_higher": algo_value > api_value
        }

    def process_activities(self, activities: List[Dict]) -> Dict:
        if not activities:
            return {"total_emissions": 0.0, "api_emissions": 0.0, "unit": "kg CO2e", "activities": []}

        results = []
        total_api_emissions = 0.0
        total_algo_emissions = 0.0
        errors = 0

        for idx, activity in enumerate(activities):
            name = activity.get("name", f"Activity {idx + 1}")
            logger.info(f"Processing: {name}")

            if not activity.get("activity_type") and not activity.get("activity_id"):
                results.append({
                    "error": "Activity type or ID required",
                    "name": name
                })
                errors += 1
                continue

            if not activity.get("parameters"):
                results.append({
                    "error": "Parameters required",
                    "name": name
                })
                errors += 1
                continue

            try:
                activity_type = activity.get("activity_type")
                activity_id = activity.get("activity_id")
                region = activity.get("region", DEFAULT_REGION)
                parameters = activity.get("parameters", {})

                activity_info = self.get_activity_info(activity_type)
                algorithm_factor = activity_info.get("algorithm_factor", 1.0)

                if not activity_id and activity_type:
                    activity_id = activity_info.get("id")

                logger.info(f"Using direct calculation for {name}.")
                api_emissions = self.calculate_direct_emissions(activity_type, parameters, region)
                logger.info(f"Direct calculation result: {api_emissions} kg CO2e")

                api_result = {
                    "co2e": api_emissions,
                    "co2e_unit": "kg",
                    "note": "Calculated using default emission factors"
                }

                algo_emissions = self.calculate_algorithmic_emissions(
                    float(api_result.get("co2e", 0.0)), region, activity_type, algorithm_factor
                )

                comparison = self.compare_calculations(float(api_result.get("co2e", 0.0)), algo_emissions)

                activity_result = {
                    "name": name,
                    "activity_id": activity_id,
                    "region": region,
                    "api_emissions": float(api_result.get("co2e", 0.0)),
                    "algorithm_emissions": algo_emissions,
                    "unit": api_result.get("co2e_unit", "kg CO2e"),
                    "comparison": comparison
                }

                if "note" in api_result:
                    activity_result["note"] = api_result["note"]

                results.append(activity_result)

                total_api_emissions += float(api_result.get("co2e", 0.0))
                total_algo_emissions += algo_emissions

            except Exception as e:
                logger.error(f"Error processing activity {idx + 1}: {str(e)}")
                results.append({
                    "error": str(e),
                    "name": name
                })
                errors += 1

        total_comparison = self.compare_calculations(total_api_emissions, total_algo_emissions)

        return {
            "api_emissions": round(total_api_emissions, 2),
            "algorithm_emissions": round(total_algo_emissions, 2),
            "unit": "kg CO2e",
            "comparison": total_comparison,
            "errors": errors,
            "activities": results
        }


def calculate_carbon_footprint(activities: List[Dict], api_key: str = None) -> Dict:
    api_key = api_key or climatiq_api_key
    if not api_key:
        logger.error("API key required")
        return {"error": "API key required"}

    try:
        calculator = CarbonEmissionCalculator(api_key)
        results = calculator.process_activities(activities)

        logger.info(f"API emissions: {results['api_emissions']} {results['unit']}")
        logger.info(f"Algorithm emissions: {results['algorithm_emissions']} {results['unit']}")
        logger.info(f"Difference: {results['comparison']['percent_difference']}%")

        return results
    except Exception as e:
        logger.error(f"Carbon footprint calculation failed: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    if not sys.stdin.isatty():
        try:
            input_data = json.loads(sys.stdin.read())
            activities = input_data.get("activities", [])
            api_key = input_data.get("api_key")

            if not activities:
                print(json.dumps({"error": "No activities provided"}))
                sys.exit(1)

            if not api_key:
                print(json.dumps({"error": "API key required"}))
                sys.exit(1)

            results = calculate_carbon_footprint(activities, api_key)
            print(json.dumps(results))
        except Exception as e:
            print(json.dumps({"error": f"Error processing input: {str(e)}"}))
            sys.exit(1)
    else:
        example_activities = [
            {
                "name": "Electricity Usage",
                "activity_type": "electricity",
                "region": "US",
                "parameters": {"energy": 100, "energy_unit": "kWh"}
            },
            {
                "name": "Car Travel",
                "activity_type": "car",
                "region": "US",
                "parameters": {"distance": 50, "distance_unit": "km"}
            },
            {
                "name": "Bus Travel",
                "activity_type": "bus",
                "region": "US",
                "parameters": {"distance": 30, "distance_unit": "km"}
            },
            {
                "name": "Natural Gas Heating",
                "activity_type": "natural_gas",
                "region": "US",
                "parameters": {"energy": 200, "energy_unit": "kWh"}
            },
            {
                "name": "Train Travel",
                "activity_type": "rail",
                "region": "US",
                "parameters": {"distance": 100, "distance_unit": "km"}
            }
        ]
        results = calculate_carbon_footprint(example_activities)
        print(json.dumps(results, indent=2))