import argparse
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

def main():
    # parse args 
    parser = argparse.ArgumentParser()
    parser.add_argument("language")
    parser.add_argument("--big", action="store_true")
    args = parser.parse_args()
    language = args.language 
    big = args.big 

    if(big):
        file_path = "./BEAR-big/english/metadata_relations.json"
        out_path = f"./BEAR-big/{language}/metadata_relations.json"
    else:
        file_path = "./BEAR/english/metadata_relations.json"
        out_path = f"./BEAR/{language}/metadata_relations.json"




    #load .env file 
    load_dotenv()
    api_url = os.getenv("OPENAI_API_PATH")
    api_key = os.getenv("OPENAI_API_KEY")
    english_examples = os.getenv("ENGLISH_EXAMPLES")
    language_examples = os.getenv("TRANSLATION_EXAMPLES")
    english_examples2 = os.getenv("ENGLISH_EXAMPLES2")
    language_examples2 = os.getenv("TRANSLATION_EXAMPLES2")
    english_examples3 = os.getenv("ENGLISH_EXAMPLES3")
    language_examples3 = os.getenv("TRANSLATION_EXAMPLES3")

    #init LLM api client
    model_index = 0
    client = OpenAI(base_url=api_url, api_key=api_key)
    model_id = client.models.list().data[model_index].id

    #open up metadata relations file 
    with open(file_path, "r") as file:
        metadate_relations = json.load(file)
    print(f"api url {api_url} api key {api_key} file path {file_path} language {language}")

    #translation_prompt = "Translate these templates to {language}, so that it is still compatible as a completion quiz template. All of the templates should be translated. Output only the tranlations seperated by line. The translated templates should be unique there shouldn't be duplicates. This is an example {english_examples} translated: {language_examples}. Here are the templates in english that need to be translated to {language}: {templates}"
    translation_prompt = "Background: Translate these templates into {language}, so that they remain compatible as a completion quiz template. All of the templates should be translated. Output only the tranlations separated by line. The translated templates should be unique there shouldn't be duplicates. The following are examples of correct translations and their corresponding original templates" \
    "Original Templates: {english_examples} Templates translated to {language}: {language_examples} " \
    "\n Original Templates: {english_examples2} Templates translated to {language}: {language_examples2} " \
    "\n Original Templates: {english_examples3} Templates translated to {language} " \
    "\n Task: English templates: {templates}"


    validation_prompt = "Background: Double check that this translation still works as a completion quiz template." \
    "The following are examples of correct translations and the origional templates\n" \
    "Original Templates: {english_examples} Templates translated to {language}: {language_examples} " \
    "\n Original Templates: {english_examples2} Templates translated to {language}: {language_examples2} " \
    "\n Original Templates: {english_examples3} Templates translated to {language}: {language_examples3} " \
    "\n Validation Rules:\n"\
    "- Each translated template must preserve the meaning of its original template.\n"\
    "- Each translated template must work as a completion quiz template.\n"\
    "- Preserve the [X] and [Y] placeholders exactly.\n"\
    "- Return the same number of templates as the number of original templates.\n "\
    "- All translated templates must be unique; there must be no duplicates.\n" \
    "- If all templates are valid, return only the word true."\
    "- If any templates are invalid, return the complete corrected set of templates, one per line. Do not include explanations or any other text.\n"\
    "Task: English Templates: {templates}\n {language} Templates {translations}.  "


    translations ={}
    #for key in dict 
    count = 0
    valid_count = 0
    skipped = []
    X_before_Y = 0
    X_before_Y_translated = 0
    for p in metadate_relations:
        
        #get templates 
        templates = metadate_relations[p].get("templates", None)

        #count X before Y occurances 
        for sentence in templates:
            x_index, y_index = sentence.find("[X]"), sentence.find("[Y]")
            if(x_index < y_index):
                X_before_Y += 1

        if not templates:
            continue
        #call translation api 
        chat_completion = client.chat.completions.create(messages=[{"role": "user", "content":translation_prompt.format(templates=templates, language=language, english_examples=english_examples, language_examples=language_examples, english_examples2=english_examples2, language_examples2=language_examples2, english_examples3=english_examples3, language_examples3=language_examples3)}], model=model_id)

        #print(f"translation prompt {translation_prompt.format(templates=templates, language=language, english_examples=english_examples, language_examples=language_examples,  english_examples2=english_examples2, language_examples2=language_examples2, english_examples3=english_examples3, language_examples3=language_examples3)}")
        translated_templates = chat_completion.choices[0].message.content
        
        #validate translation still works.
        valid = False 
        for i in range(4):
            #validate translations with model
            chat_completion = client.chat.completions.create(messages=[{"role": "user", "content":validation_prompt.format(language=language, templates=templates, translations=translated_templates,english_examples=english_examples, language_examples=language_examples,  english_examples2=english_examples2, language_examples2=language_examples2, english_examples3=english_examples3, language_examples3=language_examples3)}], model=model_id)
            validation_output = chat_completion.choices[0].message.content
            #convert translation to a list 
            translated_list = translated_templates.splitlines()
            #Check that LLM validation passed, there are three templates, and templates are unique via exact string match. 
            if(validation_output.strip()[:4].lower() == "true" ):
                if( len(translated_list) == len(templates) and len(translated_list) == len(set(translated_list))):
                    valid = True
                    break
                if i < 2:
                # Ask for a corrected translation on the next attempt.
                    print(f"programatic checks failed {translated_templates}")
                    continue
            else:
                print(f"validator didn't return true for:\n {translated_templates}")
                print(f"validator correction:\n {validation_output}")
                print("##############\n############")

                translated_templates = validation_output
        if valid:
            translations[p]= {"templates" : translated_templates.splitlines()}
            valid_count += 1
            #count X before Y occurances
            for sentence in translated_templates.splitlines():
                x_index, y_index = sentence.find("[X]"), sentence.find("[Y]")
                if(x_index < y_index):
                    X_before_Y_translated += 1
        else:
            skipped.append({p: {"templates": templates}})
            #print(f"output after three failures: {validation_output}, \n translation:\n {translated_templates}")
        count += 1

    #create dir if needed
    language_folder = os.path.dirname(out_path)
    os.makedirs(language_folder, exist_ok=True) 


    #write to new file
    with open(out_path, "w") as f:
        f.write(json.dumps(translations))


    metadata_path = os.path.join(
        language_folder,
        "metadata_translation_info.json"
    )

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({ "total": count, "translated": valid_count, "skipped": skipped, "XY_english": X_before_Y / (3.0 * count) , "XY_translated": X_before_Y_translated/ (3.0*valid_count)},f,indent=2)

if __name__ == "__main__":
    main()