from openai import AzureOpenAI
from airspeed import Template
from tqdm import tqdm
from configparser import ConfigParser
from ReplaceEncoding import ReplaceEncoding as RN
import pandas as pd
import concurrent.futures, time, os
import shutil
import httpx, json

from utility import get_logger

logger = get_logger()
class GenerateMetadata:


    def executeMetadata(client, config_dict, final_list):
        try:
            logger.info("Processing Metadata ..........")
            GenerateMetadata.write_to_file(client, config_dict, final_list)
        except Exception as e:
            logger.error(f"Error while generating Metadata: {e}")
            raise e
        
    def executeMetadata_static(client, config_dict, final_list):
        try:
            logger.info("Processing Metadata ..........")
            GenerateMetadata.write_to_file(client, config_dict, final_list)
        except Exception as e:
            logger.error(f"Error while generating Metadata: {e}")
            raise e
        
    # Function to configure Gemini model values

    def configure_client():
        config = ConfigParser()

        try:
            config.read('config.properties')

            if len(config.sections()) == 0:
                raise Exception("configuration file empty")

            max_workers = int(config['ChatGPT']['MAX_WORKERS'])
            APIM_BASE = config['ChatGPT']['APIM_BASE']
            APIM_key = config['ChatGPT']['APIM_key']
            API_VERSION = config['ChatGPT']['API_VERSION']

            client = AzureOpenAI(
                azure_endpoint=APIM_BASE,
                api_key=APIM_key,
                api_version=API_VERSION,
                http_client=httpx.Client(verify=False)
            )
        except Exception as e:
            logger.error(f"{e}")
            raise e
        return client

    # Gemini call for Metadata

    def concurrent_api_call(client, config_dict, prompt_template, model, cleaned_data_dict_list):

        def api_call(json_data):
            max_retry = 3
            retry = 0

            while retry < max_retry:
                try:
                    # logger.info(f"Input: {json_data}")
                    
                    prompt = Template(prompt_template).merge({"json_data": json.dumps(json_data, indent=4, ensure_ascii=False)})
                    # logger.info(f"prompt: {prompt}")
                    
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=float(config_dict['temperature'])
                    )
                    
                    output_json_string = response.choices[0].message.content

                    # Remove unwanted parts from the output
                    output_json_string = output_json_string.replace("json", "").replace("`", '').replace("\n", '').replace("\\", '')

                    logger.info(f"output_json_string:{output_json_string}")

                    output_data = json.loads(output_json_string)
                    # rectify currency symbol encoding 
                    output_data = RN.rectify_Metadata_response(output_data)
                
                    # Extract key-value pairs from the 'dict' field
                    if 'dict' in output_data:
                        for i in range(1, len(output_data['dict'])//2 + 1):
                            key = output_data['dict'].get(f"key{i}")
                            value = output_data['dict'].get(f"value{i}")
                            if key and value:
                                tag_list.append({key: value})
                

                    break
                except Exception as e:
                    retry += 1
                    time.sleep(1)
                    logger.error(f"Error during API call: {e}")

                    if retry == max_retry:
                        logger.error("Max retries reached, raising exception.")
                        raise e

        tag_list = []
       
        condition_order = [item["index"] for item in cleaned_data_dict_list]
        max_workers = int(config_dict["max_workers"])
        logger.info(max_workers)

        logger.info(f"Condition Order: {condition_order}")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(tqdm(executor.map(api_call, cleaned_data_dict_list), total=len(cleaned_data_dict_list), desc='PARSING metadata'))

            # GenerateMetadata.Autojsoncleanup(config_dict)
        except Exception as e:
            logger.error(e)
            raise e
    
        return tag_list
    
    def Autojsoncleanup(config_dict):
        if config_dict['AutoCleanup'].lower() == "true":
            file_name_without_extension = os.path.splitext(config_dict['file_name'])[0]
            json_fileLoc = config_dict['tempDirLoc'] + config_dict['PROJECTNAME'] + "_" + file_name_without_extension
            
            # Check if the folder exists, if so delete it
            if os.path.exists(json_fileLoc):
                shutil.rmtree(json_fileLoc)  # Remove directory and its contents
                logger.info(f"Folder deleted successfully: {json_fileLoc}")
            else:
                logger.error(f"Folder does not exist: {json_fileLoc}")

    # Function to write data to output file
    def write_to_file(client, config_dict, final_list):
        try: 
            final_tags = []
            prompt_template = config_dict['MetadatapromptLoc']
            model = config_dict['model']
            IMAGE_NAME = config_dict['IMAGE_NAME']
            OUTPUT_FOLDER = config_dict['OUTPUT_FOLDER']
            final_tags = GenerateMetadata.concurrent_api_call(client, config_dict, prompt_template, model, final_list)
            
            logger.info(f"Final tag list: {final_tags}")

            unique_pairs = list({(k, v) for d in final_tags for k, v in d.items()})

            # Convert the set of unique pairs to a DataFrame
            df = pd.DataFrame(unique_pairs, columns=['Field Name', 'Type of Master'])

            # Add an additional column with blank values for 'Line Level / Header'
            df['Line Level / Header'] = ''

            # Sort the DataFrame by 'Field Name' in ascending order
            df = df.sort_values(by='Field Name', ascending=True)

            # Reset the index if needed
            df.reset_index(drop=True, inplace=True)
            
            output_filename = os.path.join(OUTPUT_FOLDER, os.path.splitext(IMAGE_NAME)[0] + "_Metadata.xlsx")
            
            logger.info(f"output_filename: {output_filename}")
            # df.to_excel(output_filename, index=False, encoding='utf-8')
            df.to_excel(output_filename, index=False)

        except Exception as e:
            logger.error(f"Error while generating Metadata output file: {e}")
            raise e

if __name__ == "__main__":
    logger.info("Starting metadata....")
    
    config_dict={}
    
    config = ConfigParser()
    config.read('config.properties')
    
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
    config_dict['MetadatapromptLoc'] = open(config['Input Output']['MetadatapromptLoc'],'r').read()
   

    with open("Output/image22_gpt_op.json", 'r') as json_file:
        final_json_list = json.load(json_file)

    client = GenerateMetadata.configure_client()

    GenerateMetadata.executeMetadata_static(client, config_dict, final_json_list)
