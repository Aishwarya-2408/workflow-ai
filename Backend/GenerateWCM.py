from airspeed import Template
from ReplaceEncoding import ReplaceEncoding as RN
from configparser import ConfigParser
from tqdm import tqdm
from openai import AzureOpenAI
import pandas as pd
import json, concurrent,time
import re,os, httpx
from utility import get_logger

logger = get_logger()

class GenerateWCM:
    
    @staticmethod
    def read_and_parse_json(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data
        except Exception as e:
            logger.error(f"Error reading JSON file: {e}")
            return None

    def executeWCM(client, config_dict, cleaned_data_dict_list):
        try:
            logger.info("Processing WCM ..........")
            GenerateWCM.write_to_file(client, config_dict, cleaned_data_dict_list)
        except Exception as e:
            logger.error(f"Error while generating WCM: {e}")
            raise e


    # Gemini call for WCM
    def concurrent_api_call(client,config_dict, prompt_template, model, cleaned_data_dict_list):

        def api_call(json_data):
            max_retry = 3
            retry = 0

            while retry < max_retry:
                try:
                    logger.info(f"Input: {json_data}")
                    
                    prompt = Template(prompt_template).merge({"json_data": json.dumps(json_data, indent=4)})
                    # logger.info(f"prompt: {prompt}")
                    
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=float(config_dict['temperature'])
                    )
                    
                    
                    output_json_string = response.choices[0].message.content
                    output_json_string = output_json_string.replace("json", "").replace("`", "").strip()
                    if not output_json_string.startswith("["):
                        output_json_string = "[" + output_json_string.replace("}\n\n\n\n{", "},{") + "]"
                        
                    
                    output = GenerateWCM.extract_json_element(output_json_string)
                    logger.info(f"\noutput: {output}")
                    output_json = json.loads(output)

                    if output_json:
                        input_str = output_json["Condition"]
                        output_str = GenerateWCM.process_string(input_str)

                        logger.info(f"output_str= {output_str}")
                        # Assign the modified string back to the JSON
                        output_json["Condition"] = output_str

                        output_json = RN.rectify_genai_response(output_json)
                        final_json_list.append(output_json)
                    break
                except Exception as e:
                    retry = retry + 1
                    time.sleep(1)
                    logger.error(f"Error during API call: {e}")

                    if (retry == max_retry-1):
                        logger.error(output)
                        raise e
            
 
        final_json_list=[]
        condition_order = [item["index"] for item in cleaned_data_dict_list]
        max_workers= int(config_dict["max_workers"])
        logger.info(f"max- workers: {max_workers}")

        logger.info(f"condition_order:{condition_order}")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(tqdm(executor.map(api_call, cleaned_data_dict_list), total=len(cleaned_data_dict_list), desc='PARSING WCM'))
        
            grouped_data = {}
            for item in final_json_list:
                idx = item['index']
                if idx not in grouped_data:
                    grouped_data[idx] = []
                grouped_data[idx].append(item)

            # Create the ordered list based on condition_order
            ordered_data = []
            for idx in condition_order:
                ordered_data.extend(grouped_data.get(idx, []))

        except Exception as e:
            logger.error(e)
            raise e
        
        return ordered_data

    # Function to remoave space in response
    def process_string(input_str):
        # Step 1: Split the string on '&&'
        parts = input_str.split('&&') if '&&' in input_str else [input_str]

        # Step 2: Remove spaces from the keys but not from the values
        processed_parts = []
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)  # Split only on the first '='
                key = key.replace(' ', '')  # Remove spaces from the key
                processed_parts.append(f"{key}={value}")
            else:
                # If no '=' is found, add the part unchanged
                processed_parts.append(part)

        # Step 3: Merge the processed parts back with '&&' and return the string
        return '&&'.join(processed_parts)


    
    # Function to write data to output file
    def write_to_file(client, config_dict, cleaned_data_dict_list):
        try: 
            final_json_list = []
            model = config_dict['model']
            OUTPUT_FOLDER = config_dict['OUTPUT_FOLDER']
            IMAGE_NAME = config_dict['IMAGE_NAME']
            prompt_template = config_dict['WCMpromptLoc']

            final_json_list = GenerateWCM.concurrent_api_call(client, config_dict, prompt_template, model, cleaned_data_dict_list)

            outputdf = pd.DataFrame(final_json_list)
            output_filename = os.path.join(OUTPUT_FOLDER, os.path.splitext(IMAGE_NAME)[0] + "_WCM.xlsx")

            # Dropping index column to maintain expected format of output file
            if 'index' in outputdf.columns:
                outputdf = outputdf.drop(columns=['index'])
            outputdf.to_excel(output_filename, index=False)

            logger.info(f"{output_filename} file created successfully")

        except Exception as e:
            logger.error(f"Error while generating WCM output file: {e}")
            raise e



    def extract_json_element(input_text):
        # Regular expression pattern to match JSON content within ```json ```
        pattern = r'```json\s*({(?:[^{}]|\n)*})\s*```'

        # Find all matches of JSON content
        matches = re.findall(pattern, input_text, re.DOTALL)
        matches = list(set(matches))

        if matches:
            return matches[-1]
        else:
            # Extract dict from input_text
            pattern_dict = r'{(?:[^{}]|\n)*}'
            dict_match = re.findall(pattern_dict, input_text, re.DOTALL)
            return dict_match[-1] if dict_match else input_text


    # Function to convert df to JSON
    def df_to_Json(config_dict,df):
        df = df.reset_index()
        data_dict_list = df.to_dict(orient='records')

        cleaned_data_dict_list = [
            {key: str(value).strip() for key, value in row.items() if pd.notna(value) and str(value).strip()}
            for row in data_dict_list
        ]

        # Convert the list of cleaned dictionaries to a JSON string
        json_data = json.dumps(cleaned_data_dict_list, indent=4, ensure_ascii=False)
        
        logger.info(json_data)
        WCM_json_filename = os.path.splitext(config_dict["file_name"])[0]+".json"
        with open(WCM_json_filename, 'w', encoding='utf-8') as json_file:
               json_file.write(json_data)


    
if __name__ == "__main__":
        
    config_dict={}
    
    config = ConfigParser()
    config.read('configuration.ini')
    
    config_dict["model"] = config['ChatGPT']['model']
    config_dict["APIM_key"] = config['ChatGPT']['APIM_key']
    config_dict["APIM_BASE"] = config['ChatGPT']['APIM_BASE']
    config_dict["API_VERSION"] = config['ChatGPT']['API_VERSION']
    config_dict["max_workers"] = config['ChatGPT']['max_workers']
    config_dict['max_retry'] = config['ChatGPT']['max_retry']
    config_dict['seed'] = config['ChatGPT']['seed']
    config_dict['max_tokens'] = config['ChatGPT']['max_tokens']
    config_dict["temperature"] = config['ChatGPT']['temperature']
    config_dict['IMAGE_NAME'] = config['Input Output']['IMAGE_NAME']
    config_dict['IMAGE_FOLDER'] = config['Input Output']['IMAGE_FOLDER']
    config_dict['OUTPUT_FOLDER'] = config['Input Output']['OUTPUT_FOLDER']
    config_dict['WCMpromptLoc'] = open(config['Input Output']['WCMpromptLoc'],'r').read()
   

    image_name_without_ext = os.path.splitext(config_dict['IMAGE_NAME'])[0]

    # Construct the JSON file path
    json_file_path = os.path.join(config_dict['OUTPUT_FOLDER'], f"{image_name_without_ext}_gpt_op.json")

    # Read and parse JSON data
    data = GenerateWCM.read_and_parse_json(json_file_path)
    
    
    client = AzureOpenAI(
                azure_endpoint=config_dict["APIM_BASE"],
                api_key=config_dict["APIM_key"],
                api_version=config_dict["API_VERSION"],
                http_client=httpx.Client(verify=False)
            )

    if data:
        GenerateWCM.executeWCM(client, config_dict, data)