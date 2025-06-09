from tqdm import tqdm
from configparser import ConfigParser
from openai import AzureOpenAI
import httpx
import pandas as pd
from airspeed import Template
import concurrent
import json , time , os
from utility import get_logger

logger = get_logger()

class GenerateMCW:

    @staticmethod
    def read_and_parse_json(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data
        except Exception as e:
            logger.error(f"Error reading JSON file: {e}")
            return None

    def executeMCW(client, config_dict, Intermediate_json1):
        try:
            logger.info("Processing MCW ..........")

            GenerateMCW.write_to_file(client, Intermediate_json1, config_dict)
        except Exception as e:
            logger.error(f"Error while generating MCW: {e}")
            raise e

    
    # Function to write data to output file
    def write_to_file(client, Intermediate_json, config_dict):
        try:
            final_json_list = []
            model = config_dict['model']
            OUTPUT_FOLDER = config_dict['OUTPUT_FOLDER']
            IMAGE_NAME = config_dict['IMAGE_NAME']
            prompt_template = config_dict['MCWpromptLoc']

            final_json_list = GenerateMCW.concurrent_gpt_call(client,prompt_template, model, Intermediate_json, config_dict)

            logger.info(f"final_json_list: {final_json_list}")

            # Flatten the list of lists into a single list of dictionaries
            flat_list = [item for sublist in final_json_list for item in sublist]
            output_df = pd.DataFrame(flat_list)
            output_filename = os.path.join(OUTPUT_FOLDER, os.path.splitext(IMAGE_NAME)[0] + "_MCW.xlsx")

            with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
                first_id_value = output_df['Id'].iloc[0] if 'Id' in output_df.columns and not output_df.empty else ''

                basic_info_df = pd.DataFrame({
                    'Id': [first_id_value], 
                    'Title': [''], 
                    'Process': [''],
                    'Status': ['ACTIVE'],
                    'Description': ['']
                })

                basic_info_df.to_excel(writer, index=False, sheet_name='Basic Info')

                if 'index' in output_df.columns:
                    output_df = output_df.drop(columns=['index'])
                output_df.to_excel(writer, index=False, sheet_name='Approval Path')

                workbook = writer.book
                worksheet = writer.sheets['Approval Path']

                (max_row, max_col) = output_df.shape

                for row in range(max_row):
                    for col in range(max_col):
                        cell_value = output_df.iat[row, col]
                        if isinstance(cell_value, str) and '\n' in cell_value:
                            cell_format = workbook.add_format({'text_wrap': True})
                            worksheet.write(row + 1, col, cell_value, cell_format)

            logger.info(f"{output_filename} file created successfully")
        except Exception as e:
            logger.error(f"Error while creating output file: {e}")
            raise e
        

    def concurrent_gpt_call(client,prompt_template, model, intermediate_json, config_dict):

        def api_call(json_data):
            max_retry = int (config_dict['max_retry'])
            retry = 0

            while retry < max_retry:
                try:
                    # Create prompt from template
                    prompt = Template(prompt_template).merge({"json_data": json.dumps(json_data, indent=4)})

                    # Call Azure OpenAI API
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=float(config_dict['temperature'])
                    )

                    # Extract response text
                    output_json_string = response.choices[0].message.content
                    output_json_string = output_json_string.replace("json", "").replace("`", "").strip()
                
                    # Ensure response is wrapped in a list if multiple objects are present
                    if not output_json_string.startswith("["):
                        output_json_string = "[" + output_json_string.replace("}\n\n\n\n{", "},{") + "]"

                    output_jsons = json.loads(output_json_string)  # Ensure proper parsing
                    logger.info(f"Parsed JSON objects: {output_jsons}")

                    for output in output_jsons:
                        logger.info(f"Output: {json.dumps(output, indent=4)}")
                        final_json_list.append(output)
                    break
                
                except json.JSONDecodeError as json_err:
                    logger.error(f"JSON decode error: {json_err}")
                    retry += 1
                    time.sleep(1)
                except Exception as e:
                    retry += 1
                    time.sleep(1)
                    logger.error(f"Error during API call (attempt {retry}): {e}")

                    if retry == max_retry:
                        raise e

        final_json_list = []
        condition_order = [item["index"] for item in intermediate_json]
        max_workers = 50  # Define max workers

        logger.info(f"Max Workers: {max_workers}")
        logger.info(f"Condition Order: {condition_order}")

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(tqdm(executor.map(api_call, intermediate_json), total=len(intermediate_json), desc="Processing with Azure GPT-4o"))

            grouped_data = {}
            for item in final_json_list:
                idx = item['index']
                if idx not in grouped_data:
                    grouped_data[idx] = []
                grouped_data[idx].append(item)

            
            logger.info(f"grouped_data: {grouped_data}")

            # Order data based on condition_order
            ordered_data = [grouped_data[idx] for idx in condition_order if idx in grouped_data]

        except Exception as e:
            logger.error(f"Error: {e}")
            raise e

        return ordered_data
            

   
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
    config_dict['UPLOAD_FOLDER'] = config['Input Output']['UPLOAD_FOLDER']
    config_dict['OUTPUT_FOLDER'] = config['Input Output']['OUTPUT_FOLDER']
    config_dict['MCWpromptLoc'] = open(config['Input Output']['MCWpromptLoc'],'r').read()
   

    image_name_without_ext = os.path.splitext(config_dict['IMAGE_NAME'])[0]

    # Construct the JSON file path
    json_file_path = os.path.join(config_dict['OUTPUT_FOLDER'], f"{image_name_without_ext}_gpt_op.json")

    # Read and parse JSON data
    data = GenerateMCW.read_and_parse_json(json_file_path)
    
    
    client = AzureOpenAI(
                azure_endpoint=config_dict["APIM_BASE"],
                api_key=config_dict["APIM_key"],
                api_version=config_dict["API_VERSION"],
                http_client=httpx.Client(verify=False)
            )

    if data:
        GenerateMCW.executeMCW(client, config_dict, data)
