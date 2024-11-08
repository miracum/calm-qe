from collections import defaultdict
import json
import time

from fhirclient.models.condition import Condition
from fhirclient.models.encounter import Encounter

from Constants import USER_NAME, USER_PASSWORD, ICD_SYSTEM_NAME, ASTHMA_COPD_CODES_FILE
from FhirHelpersUtils import fetch_bundle_for_code, connect_to_server
from Metadata import gather_metadata



def patients_with_asthma_copd(smart):
    """
    It reads the ASTHMA or COPD diseases related codes from "ASTHMA_COPD_CODES_FILE" and
    find the patients that have such diagnoses.
    :param smart: Fhir Server Connector
    """
    with open(ASTHMA_COPD_CODES_FILE, 'r') as file:
        main_diagnoses_file = json.load(file)
        main_diagnoses_codes = [item['code'] for item in main_diagnoses_file['codes']]
    print(main_diagnoses_codes)

    patients_conditions_map = defaultdict(list)
    for code in main_diagnoses_codes:
        while True:
            try:
                bundle = Condition.where(struct={'_count': b'1000', 'code': ICD_SYSTEM_NAME + '|' + code}).perform(smart.server)
                break
            except Exception as exc:
                print(f"Generated an exception: {exc} but continue to trying.\n")
                smart = connect_to_server(user=USER_NAME, pw=USER_PASSWORD)
                time.sleep(3)

        conditions = fetch_bundle_for_code(smart, bundle)
        if conditions:
            for entry in conditions:
                condition = entry['resource']
                if condition['subject']['reference']:
                    patient_reference = condition['subject']['reference']
                    patients_conditions_map[patient_reference].append(condition['id'])

    print(len(patients_conditions_map))
    gather_metadata("asthma_and_copd_patient_count", len(patients_conditions_map))
    with open('patients_diagnosed_asthma_copd.json', 'w') as file: #Intermediate results, can be deleted later.
        json.dump(patients_conditions_map, file, indent=4)


def filter_main_diagnosis(smart):
    """
    From the patients diagnosed ASTHMA or COPD, it filters only for HauptDiagnosis(Main) from their Encounter references.
    Put the results into JSON file format.
    :param smart: Fhir Server Connector
    """
    patients_with_chief_complaint = defaultdict(list)
    with open("patients_diagnosed_asthma_copd.json", "r") as file:
        patients = json.load(file)
        for patient in patients.keys():
            print(f"Processing patient with ID: {patient[8:]}...")
            conditions_ids = patients[patient]
            for condition in conditions_ids:
                while True: #Connection might get lost sometime, try reconnect...
                    try:
                        #Check the patient with the spesific condition ID has Encounter reference.
                        bundle = Encounter.where(struct={'_count': b'10', 'subject': patient, 'diagnosis': 'Condition/' + condition}).perform(smart.server)
                        break
                    except Exception as exc:
                        print(f"Generated an exception: {exc} but continue to trying. \n")
                        smart = connect_to_server(user=USER_NAME, pw=USER_PASSWORD)
                        time.sleep(3)

                encounter = fetch_bundle_for_code(smart, bundle)
                #If the encounter exist, check the diagnosis from this encounter is "MainDiagnose" or not. If so, put it into result.
                if encounter:
                    for enc in encounter:
                        if 'diagnosis' in enc['resource']:
                            for c in enc['resource']['diagnosis']:
                                if c['use']['coding'][0]['code'] == "CC" and ('Condition/' + condition == c['condition']['reference']): #chief complaint
                                    patients_with_chief_complaint[patient].append(condition)

    gather_metadata("asthma_and_copd_patients_with_chief_complaint", len(patients_with_chief_complaint))
    with open("patients_main_diagnosed_asthma_copd.json", "w") as out:
        json.dump(patients_with_chief_complaint, out, indent=4)


