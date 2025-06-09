import json
from utility import get_logger

logger = get_logger()

class ReplaceEncoding:
    # Map of encodings to currency symbols and their names
    currency_map = {
        "u0024": ("$", "Dollar Sign"),
        "u00a2": ("¢", "Cent Sign"),
        "u00a3": ("£", "Pound Sign"),
        "u00a4": ("¤", "Currency Sign"),
        "u00a5": ("¥", "Yen Sign"),
        "u058f": ("֏", "Armenian Dram Sign"),
        "u060b": ("؋", "Afghani Sign"),
        "u07fe": ("߾", "Nko Dorome Sign"),
        "u07ff": ("߿", "Nko Taman Sign"),
        "u09f2": ("৲", "Bengali Rupee Mark"),
        "u09f3": ("৳", "Bengali Rupee Sign"),
        "u09fb": ("৻", "Bengali Ganda Mark"),
        "u0af1": ("૱", "Gujarati Rupee Sign"),
        "u0bf9": ("௹", "Tamil Rupee Sign"),
        "u0e3f": ("฿", "Thai Currency Symbol Baht"),
        "u17db": ("៛", "Khmer Currency Symbol Riel"),
        "u20a0": ("₠", "Euro-Currency Sign"),
        "u20a1": ("₡", "Colon Sign"),
        "u20a2": ("₢", "Cruzeiro Sign"),
        "u20a3": ("₣", "French Franc Sign"),
        "u20a4": ("₤", "Lira Sign"),
        "u20a5": ("₥", "Mill Sign"),
        "u20a6": ("₦", "Naira Sign"),
        "u20a7": ("₧", "Peseta Sign"),
        "u20a8": ("₨", "Rupee Sign"),
        "u20a9": ("₩", "Won Sign"),
        "u20aa": ("₪", "New Sheqel Sign"),
        "u20ab": ("₫", "Dong Sign"),
        "u20ac": ("€", "Euro Sign"),
        "u20ad": ("₭", "Kip Sign"),
        "u20ae": ("₮", "Tugrik Sign"),
        "u20af": ("₯", "Drachma Sign"),
        "u20b0": ("₰", "German Penny Sign"),
        "u20b1": ("₱", "Peso Sign"),
        "u20b2": ("₲", "Guarani Sign"),
        "u20b3": ("₳", "Austral Sign"),
        "u20b4": ("₴", "Hryvnia Sign"),
        "u20b5": ("₵", "Cedi Sign"),
        "u20b6": ("₶", "Livre Tournois Sign"),
        "u20b7": ("₷", "Spesmilo Sign"),
        "u20b8": ("₸", "Tenge Sign"),
        "u20b9": ("₹", "Indian Rupee Sign"),
        "u20ba": ("₺", "Turkish Lira Sign"),
        "u20bb": ("₻", "Nordic Mark Sign"),
        "u20bc": ("₼", "Manat Sign"),
        "u20bd": ("₽", "Ruble Sign"),
        "u20be": ("₾", "Lari Sign"),
        "u20bf": ("₿", "Bitcoin Sign"),
        "ua838": ("꠸", "North Indic Rupee Mark"),
        "ufdfc": ("﷼", "Rial Sign"),
        "ufe69": ("﹩", "Small Dollar Sign"),
        "uff04": ("＄", "Fullwidth Dollar Sign"),
        "uffe0": ("￠", "Fullwidth Cent Sign"),
        "uffe1": ("￡", "Fullwidth Pound Sign"),
        "uffe5": ("￥", "Fullwidth Yen Sign"),
        "uffe6": ("￦", "Fullwidth Won Sign"),
        "u11fdd": ("𑿝", "Tamil Sign Kaacu"),
        "u11fde": ("𑿞", "Tamil Sign Panam"),
        "u11fdf": ("𑿟", "Tamil Sign Pon"),
        "u11fe0": ("𑿠", "Tamil Sign Varaakan"),
        "u1e2ff": ("𞋿", "Wancho Ngun Sign"),
        "u1ecb0": ("𞲰", "Indic Siyaq Rupee Mark"),
        "â‚¬": ("€","Euro symbol"),
    }

    # Function to replace encoding with symbols
    def replace_currency_symbols(data, currency_map, input_json_filename):
        for entry in data:
            for key, value in entry.items():
                if isinstance(value, str):
                    for encoding, (symbol, name) in currency_map.items():
                        if encoding.lower() in value.lower():
                            # entry[key] = value.replace(encoding, symbol)
                            entry[key] = value.replace(encoding.upper(), symbol).replace(encoding.lower(), symbol)
                            logger.info(f"\nReplaced '{encoding}' with '{symbol}' ({name}) in '{key}' in file {input_json_filename}")
        return data
    
    # Function to rectify the response JSON
    def rectify_response(response_json, currency_map):
        for key, value in response_json.items():
            if isinstance(value, str):
                for encoding, (symbol, name) in currency_map.items():
                    if encoding.lower() in value.lower():
                        response_json[key] = value.replace(encoding.upper(), symbol).replace(encoding.lower(), symbol)
                        logger.info(f"\nReplaced '{encoding}' with '{symbol}' ({name}) in '{key}' in response")
        return response_json

    # Read JSON data from file
    def read_json_from_file(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    # Write updated JSON data to file
    def write_json_to_file(data, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4,ensure_ascii=False)


    def rectify_json_file(file_path):
        # Read the JSON data
        json_data = ReplaceEncoding.read_json_from_file(file_path)

        # Replace the currency symbols in the JSON data
        updated_json = ReplaceEncoding.replace_currency_symbols(json_data, ReplaceEncoding.currency_map, file_path)

        # Write the updated JSON back to a file
        ReplaceEncoding.write_json_to_file(updated_json, file_path)

        logger.info(f"JSON updated and written to {file_path}")


    def rectify_genai_response(response_json):
        # Replace the currency symbols in the JSON data
        updated_response = ReplaceEncoding.rectify_response(response_json, ReplaceEncoding.currency_map )

        return updated_response
    
    # Function to rectify metadata prompt output json response
    def rectify_Metadata_response(response_json):
        updated_response = ReplaceEncoding.rectify_Metadata(response_json, ReplaceEncoding.currency_map )
        
        return updated_response
    

    def rectify_Metadata(response_json, currency_map):
    # Recursive function to handle nested dictionaries
        def replace_currency_in_Metadata(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        for encoding, (symbol, name) in currency_map.items():
                            if encoding.lower() in value.lower():
                                data[key] = value.replace(encoding.upper(), symbol).replace(encoding.lower(), symbol)
                                print(f"\nReplaced '{encoding}' with '{symbol}' ({name}) in '{key}' in response")
                    elif isinstance(value, dict):
                        # Recursively handle nested dictionaries
                        replace_currency_in_Metadata(value)
            return data

        return replace_currency_in_Metadata(response_json)


    