import os
import base64
import httpx, json
from openai import AzureOpenAI
from GenerateMCW import GenerateMCW
from GenerateWCM import GenerateWCM
from GenerateMetadata import GenerateMetadata
from configparser import ConfigParser
from utility import get_logger
import re

# Initialize config_dict
config_dict = {}


logger = get_logger()
class Preprocessing:
    
    # Function to read configuration.ini 
    def read_config():

        config = ConfigParser()
        try:
            config.read('configuration.ini')

            if len(config.sections()) == 0:
                raise Exception("configuration file empty")
            
            config_dict["model"] = config['ChatGPT']['model']
            config_dict["APIM_key"] = config['ChatGPT']['APIM_key']
            config_dict["APIM_BASE"] = config['ChatGPT']['APIM_BASE']
            config_dict["API_VERSION"] = config['ChatGPT']['API_VERSION']
            config_dict["max_workers"] = config['ChatGPT']['max_workers']
            config_dict['max_retry'] = config['ChatGPT']['max_retry']
            config_dict['seed'] = config['ChatGPT']['seed']
            config_dict['max_tokens'] = config['ChatGPT']['max_tokens']
            config_dict["temperature"] = config['ChatGPT']['temperature']
            config_dict['tempDirLoc'] = config['Input Output']['tempDirLoc']
            config_dict['UPLOAD_FOLDER'] = config['Input Output']['UPLOAD_DIR']
            config_dict['OUTPUT_FOLDER'] = config['Input Output']['OUTPUT_FOLDER']
            config_dict['MCWpromptLoc'] = open(config['Input Output']['MCWpromptLoc'],'r').read()
            config_dict['WCMpromptLoc'] = open(config['Input Output']['WCMpromptLoc'],'r').read()
            config_dict['MetadatapromptLoc'] = open(config['Input Output']['MetadatapromptLoc'],'r').read()
            config_dict["FetchImageData_promptLoc"] = open(config['Input Output']['FetchImageData_promptLoc'],'r').read()
            config_dict['ProcessImageData_promptLoc'] = open(config['Input Output']['ProcessImageData_promptLoc'],'r').read()

        except Exception as e:
            logger.error(f"{e}")
            raise e
        
        return config_dict
    
    # Function to configure Gemini model values
    def configure_client():
        config = ConfigParser()

        try:
            config.read('configuration.ini')

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
    

    def analyze_workflow_image(client, config_dict):

        IMAGE_PATH = os.path.join(config_dict['UPLOAD_FOLDER'], config_dict['IMAGE_NAME'])
        # Read the image file
        with open(IMAGE_PATH, "rb") as image_file:

            prompt = config_dict['FetchImageData_promptLoc']
            # Call OpenAI API to analyze image
            response = client.chat.completions.create(
                model=config_dict['model'],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode()}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens= int(config_dict['max_tokens']),
                seed= int(config_dict['seed']),
                temperature= float(config_dict['temperature'])
            )
            
            workflow_data = response.choices[0].message.content        

            return workflow_data


    def generateConditionandApprover(config_dict, workflow_data, client):

        prompt2= config_dict['ProcessImageData_promptLoc']
        model = config_dict['model']

        response = client.chat.completions.create(
            model=model,
            messages=[
                {

                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt2},
                        {"type": "text", "text": workflow_data}  # Passing summary instead of image
                    ]
                }
            ],
            max_tokens=2000,
            seed=100,
            temperature=0
        )

        Intermediate_json = response.choices[0].message.content  
        
        return Intermediate_json


    def parse_json_objects(content):
        # Use regex to find all JSON objects in the content
        json_objects = re.findall(r'\{[\s\S]*?\}', content)
        parsed_objects = []

        for obj in json_objects:
            try:
                parsed_object = json.loads(obj)
                parsed_objects.append(parsed_object)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error("Raw content:", obj)  # For debugging

        return parsed_objects

    def process_output_json(content):
        # Parse JSON objects from the content
        parsed_objects = Preprocessing.parse_json_objects(content)

        # Process each parsed JSON object
        for obj in parsed_objects:
            # Perform any additional processing if needed
            logger.info(obj)

        return parsed_objects

    def main():

        config_dict = Preprocessing.read_config() 
        client=  Preprocessing.configure_client()

        # Create output filename based on input filename
        output_file = os.path.join(config_dict['OUTPUT_FOLDER'], os.path.splitext(config_dict['IMAGE_NAME'])[0] + "_gpt_op.json")
        
        try:
            # Analyze the workflow image
            workflow_data = Preprocessing.analyze_workflow_image(client, config_dict)

            logger.info(f"Image Extract: {workflow_data}")

            extract_file = os.path.join(config_dict['OUTPUT_FOLDER'], os.path.splitext(config_dict['IMAGE_NAME'])[0] + "_gpt_extract.txt")

            # Write the workflow data to the file
            with open(extract_file, "w", encoding="utf-8") as file:
                file.write("Workflow Summary:\n")
                file.write(str(workflow_data))

            logger.info("********************************************************")
            logger.info("\n")

            Intermediate_json = Preprocessing.generateConditionandApprover(config_dict,workflow_data, client)

            logger.info(f"Intermediate_json:{Intermediate_json}")

            if isinstance(Intermediate_json, str):
                Intermediate_json = Intermediate_json.strip("```json\n")  # Remove formatting if any

            parsed_json_list = Preprocessing.process_output_json(Intermediate_json)
            with open(output_file, 'w') as f:
                json.dump(parsed_json_list, f, indent=2,ensure_ascii=False)

            # GenerateMCW.executeMCW(client, config_dict, parsed_json_list)
            # GenerateWCM.executeWCM(client, config_dict, parsed_json_list)
            # GenerateMetadata.executeMetadata(client, config_dict, parsed_json_list)
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}") 

    
    
if __name__ == "__main__":
    
    Preprocessing.main()