import os
from pprint import pprint

import tid_pb2
import tid_pb2_grpc
from grpc_health.v1 import (
    health_pb2,
    health_pb2_grpc,
)
import grpc
from concurrent import futures
import logging
from signal import signal, SIGTERM
import json
from time import time
from google.protobuf.timestamp_pb2 import Timestamp
import query_pb2, query_pb2_grpc

jaeger_host = os.getenv("JAEGER_HOST", "localhost")
jaeger_port = os.getenv("JAEGER_QUERY_PORT", "16685")
jaeger_channel = grpc.insecure_channel(
    f"{jaeger_host}:{jaeger_port}"
)
jaeger_server = query_pb2_grpc.QueryServiceStub(jaeger_channel)


class TIDService(tid_pb2_grpc.TIDictServicer):

    def Check(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING)

    def Watch(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.UNIMPLEMENTED)

    # builds data disclosed property in TIL object
    def GetDataDisclosedOfType(self, keyword, context):
        ti_dict = read_ti_dict()
        result_list = []
        if keyword.value == tid_pb2.CATEGORY:
            for i in range(len(ti_dict["dataDisclosed"]["category"])):
                category = tid_pb2.Category(
                    id=ti_dict["dataDisclosed"]["category"][i]["id"],
                    value=ti_dict["dataDisclosed"]["category"][i]["value"]
                )
                result_list.append(tid_pb2.DataDisclosedEntry(category=category))
        elif keyword.value == tid_pb2.PURPOSE:
            purpose_list = ti_dict["dataDisclosed"]["purposes"]
            for i in range(len(purpose_list)):
                purpose = create_purpose(purpose_list[i])
                result_list.append(tid_pb2.DataDisclosedEntry(purpose=purpose))
        elif keyword.value == tid_pb2.LEGAL_BASE:
            legal_base_list = ti_dict["dataDisclosed"]["legalBase"]
            for i in range(len(legal_base_list)):
                result_list.append(tid_pb2.DataDisclosedEntry(
                    legal_base=create_legal_base(legal_base_list[i]))
                )
        elif keyword.value == tid_pb2.RECIPIENT:
            recipient_list = ti_dict["dataDisclosed"]["recipient"]
            for i in range(len(recipient_list)):
                result_list.append(tid_pb2.DataDisclosedEntry(
                    recipient=create_recipient(recipient_list[i]))
                )
        elif keyword.value == tid_pb2.STORAGE:
            if "temporal" in ti_dict["dataDisclosed"]["storage"].keys():
                storage_attributes = ti_dict["dataDisclosed"]["storage"]["temporal"]
                for i in range(len(storage_attributes)):
                    result_list.append(tid_pb2.DataDisclosedEntry(
                        storage=create_storage(storage_attributes[i], "temporal"))
                    )
            if "purposeConditional" in ti_dict["dataDisclosed"]["storage"].keys():
                storage_attributes = ti_dict["dataDisclosed"]["storage"]["purposeConditional"]
                for i in range(len(storage_attributes)):
                    result_list.append(tid_pb2.DataDisclosedEntry(
                        storage=create_storage(storage_attributes[i], "purposeConditional"))
                    )
            if "legalBasisConditional" in ti_dict["dataDisclosed"]["storage"].keys():
                storage_attributes = ti_dict["dataDisclosed"]["storage"]["legalBasisConditional"]
                for i in range(len(storage_attributes)):
                    result_list.append(tid_pb2.DataDisclosedEntry(
                        storage=create_storage(storage_attributes[i], "legalBasisConditional"))
                    )
        else:
            # does not match DataDisclosedType
            result_list = [tid_pb2.DataDisclosedEntry()]
            result_list[0].null_value = tid_pb2.NULL_VALUE
        return tid_pb2.DataDisclosedResponse(list=result_list)

    # builds GetThirdCountryTransfers in TIL object
    def GetThirdCountryTransfers(self, nothing, context):
        ti_dict = read_ti_dict()
        third_country_transfers = []
        if "thirdCountryTransfers" in ti_dict.keys():
            third_country_transfers += ti_dict["thirdCountryTransfers"]
        for i in range(len(third_country_transfers)):
            third_country_transfers[i] = construct_third_country_transfer_item(third_country_transfers[i])
        return tid_pb2.TCTResponse(third_country_transfers=third_country_transfers)

    # builds GetChangesOfPurpose in TIL object
    def GetChangesOfPurpose(self, nothing, context):
        ti_dict = read_ti_dict()
        changes_of_purposes = []
        if "changesOfPurpose" in ti_dict.keys():
            changes_of_purposes += ti_dict["changesOfPurpose"]
        for i in range(len(changes_of_purposes)):
            changes_of_purposes[i] = construct_change_of_purpose_item(changes_of_purposes[i])
        return tid_pb2.COPResponse(changes_of_purposes=changes_of_purposes)

    # function filters the JSON that is delivered by Jaeger for tags
    def GetTransparencyInformationFromTagList(self, tag_list, context):
        tags_str = tag_list.tags
        for char in '[] \"':
            tags_str = tags_str.replace(char, '')
        tags = tags_str.split(",")
        tid_entries = []
        # print("GetTransparencyInformationFromTagList(" + str(tags) + ")")  # debugging
        for tag in tags:
            search_result = search_json_for_tag(tag)
            if search_result is not None:
                tid_entries.append(search_result)
            else:
                raise LookupError("not found: " + tag)
        return construct_transparency_information_item(tid_entries)

    # Queries the Jaeger backend regarding all services and traces of the last x minutes
    def GetTransparencyInformationFromTraces(self, request, context):
        minutes = request.cover_traces_of_the_last_x_min if request.cover_traces_of_the_last_x_min > 0 else 5
        print("\nGetTransparencyInformationFromTraces(" + str(minutes) + "):")
        start_time_min = int(time()) - (minutes * 60)
        ti_tags = {}
        print("  jaeger_server.GetServices()")
        get_services_response = jaeger_server.GetServices(query_pb2.GetServicesRequest())
        for service in get_services_response.services:
            if service != "jaeger-query":  # always in the response, not interesting for us
                trace_query = query_pb2.TraceQueryParameters(
                    service_name=service,
                    start_time_min=Timestamp(seconds=start_time_min)
                )
                print("  jaeger_server.FindTraces(" + str(service) + ")")
                response = jaeger_server.FindTraces(query_pb2.FindTracesRequest(query=trace_query))
                for chunk in list(response):
                    for span in chunk.spans:
                        if span.process.service_name not in ti_tags.keys():
                            ti_tags[span.process.service_name] = {}
                        for tag in span.tags:
                            if tag.key.startswith("ti_"):
                                ti_tags[span.process.service_name][tag.key] = tag.v_str
        # print("  tag lists by service:")
        pprint(ti_tags)
        services_tilt_objects = {}
        for service in ti_tags.keys():
            services_tilt_objects[service] = {
                "data_disclosed_entries": [],
                "third_country_transfers": [],
                "changes_of_purposes": []
            }
            for tag_list in ti_tags[service].values():
                response = self.GetTransparencyInformationFromTagList(
                    tid_pb2.TagListRequest(tags=tag_list), None
                )
                if response.HasField("data_disclosed"):
                    services_tilt_objects[service]["data_disclosed_entries"].append(response.data_disclosed)
                elif response.HasField("third_country_transfer"):
                    services_tilt_objects[service]["third_country_transfers"].append(response.third_country_transfer)
                elif response.HasField("change_of_purpose"):
                    services_tilt_objects[service]["changes_of_purposes"].append(response.change_of_purpose)
        # print("  tilt objects by service:")
        # pprint(services_tilt_objects)
        return construct_ti_response(services_tilt_objects)


def construct_ti_response(services_tilt_objects) -> tid_pb2.TransparencyInformationResponse:
    services = []
    for service in services_tilt_objects.keys():
        services.append(tid_pb2.TransparencyInformationResponse.ServiceRelatedTransparencyInformation(
            service=service,
            data_disclosed_entries=services_tilt_objects[service]["data_disclosed_entries"],
            third_country_transfers=services_tilt_objects[service]["third_country_transfers"],
            changes_of_purposes=services_tilt_objects[service]["changes_of_purposes"]
        ))
    return tid_pb2.TransparencyInformationResponse(services=services)


# TIL object is actually build here
def construct_transparency_information_item(tid_entries) -> tid_pb2.TagListResponse:
    first_entry = tid_entries[0]
    if "dd_type" in first_entry.keys() and first_entry["dd_type"] == "category":
        ti_item = construct_data_disclosed_item(tid_entries)
        return tid_pb2.TagListResponse(
            data_disclosed=ti_item
        )
    elif "ti_type" in first_entry.keys() and first_entry["ti_type"] == "thirdCountryTransfers":
        ti_item = construct_third_country_transfer_item(first_entry)
        return tid_pb2.TagListResponse(
            third_country_transfer=ti_item
        )
    elif "ti_type" in first_entry.keys() and first_entry["ti_type"] == "changesOfPurpose":
        ti_item = construct_change_of_purpose_item(first_entry)
        return tid_pb2.TagListResponse(
            change_of_purpose=ti_item
        )
    else:
        raise ValueError("Entry '" + str(first_entry) + "' does not match supported Transparency Information types." +
                         "\nComplete list: " + str(tid_entries))


def construct_third_country_transfer_item(tct_item) -> tid_pb2.ThirdCountryTransfer:
    if "adequacyDecision" in tct_item.keys() and "available" in tct_item["adequacyDecision"].keys():
        adequacy_decision = tid_pb2.ThirdCountryTransfer.AdequacyDecision(
            available=tct_item["adequacyDecision"]["available"],
            description=if_exists(tct_item["adequacyDecision"], "description")
        )
    else:
        adequacy_decision = tid_pb2.ThirdCountryTransfer.AdequacyDecision(available=False)
    if "appropriateGuarantees" in tct_item.keys() and "available" in tct_item["appropriateGuarantees"].keys():
        appropriate_guarantees = tid_pb2.ThirdCountryTransfer.AppropriateGuarantees(
            available=tct_item["appropriateGuarantees"]["available"],
            description=if_exists(tct_item["appropriateGuarantees"], "description")
        )
    else:
        appropriate_guarantees = tid_pb2.ThirdCountryTransfer.AppropriateGuarantees(available=False)
    if "presenceOfEnforceableRightsAndEffectiveRemedies" in tct_item.keys() \
            and "available" in tct_item["presenceOfEnforceableRightsAndEffectiveRemedies"].keys():
        presence_of_enforceable_rights_and_effective_remedies = \
            tid_pb2.ThirdCountryTransfer.PresenceOfEnforceableRightsAndEffectiveRemedies(
                available=tct_item["presenceOfEnforceableRightsAndEffectiveRemedies"]["available"],
                description=if_exists(tct_item["presenceOfEnforceableRightsAndEffectiveRemedies"], "description")
            )
    else:
        presence_of_enforceable_rights_and_effective_remedies = \
            tid_pb2.ThirdCountryTransfer.PresenceOfEnforceableRightsAndEffectiveRemedies(available=False)
    if "standardDataProtectionClause" in tct_item.keys() \
            and "available" in tct_item["standardDataProtectionClause"].keys():
        standard_data_protection_clause = tid_pb2.ThirdCountryTransfer.StandardDataProtectionClause(
            available=tct_item["standardDataProtectionClause"]["available"],
            description=if_exists(tct_item["standardDataProtectionClause"], "description")
        )
    else:
        standard_data_protection_clause = tid_pb2.ThirdCountryTransfer.StandardDataProtectionClause(available=False)
    return tid_pb2.ThirdCountryTransfer(
        id=tct_item["id"],
        country=if_exists(tct_item, "country"),
        adequacy_decision=adequacy_decision,
        appropriate_guarantees=appropriate_guarantees,
        presence_of_enforceable_rights_and_effective_remedies=presence_of_enforceable_rights_and_effective_remedies,
        standard_data_protection_clause=standard_data_protection_clause
    )


def construct_change_of_purpose_item(cop_item) -> tid_pb2.ChangesOfPurpose:
    categories = []
    if "affectedDataCategories" in cop_item.keys():
        for item in cop_item["affectedDataCategories"]:
            category = tid_pb2.Category(
                id=item["id"],
                value=item["value"]
            )
            categories.append(category)
    return tid_pb2.ChangesOfPurpose(
        id=cop_item["id"],
        description=if_exists(cop_item, "description"),
        affected_data_categories=categories,
        planned_date_of_change=if_exists(cop_item, "plannedDateOfChange"),
        url_of_new_version=if_exists(cop_item, "urlOfNewVersion")
    )


def construct_data_disclosed_item(tid_entries) -> tid_pb2.DataDisclosed:
    dd_id = ""
    category = ""
    purposes = []
    legal_bases = []
    recipients = []
    storage_temporal = []
    storage_purpose = []
    storage_legal = []
    for dd_dict in tid_entries:
        if type(dd_dict) is not dict:
            raise TypeError("construct_data_disclosed_item():\n" +
                            "Expected type dict but got type " +
                            str(type(dd_dict)) + " for \"" + str(dd_dict) + "\".")
        if "dd_type" not in dd_dict.keys():
            raise LookupError("key dd_type not found in " + str(dd_dict))
        elif dd_dict["dd_type"] == "category":
            if category == "":
                dd_id += dd_dict["id"] + "_"
                category = dd_dict["value"]
            else:
                raise ValueError("Surplus category \"" + dd_dict["value"] + "\"\n" +
                                 "This DataDisclosed entry has already the category " +
                                 category + "\n" +
                                 "Each DataDisclosed entry should only have one category.")
        elif dd_dict["dd_type"] == "purposes":
            dd_id += dd_dict["id"] + "_"
            purposes.append(create_purpose(dd_dict))
        elif dd_dict["dd_type"] == "legalBase":
            dd_id += dd_dict["id"] + "_"
            legal_bases.append(create_legal_base(dd_dict))
        elif dd_dict["dd_type"] == "recipient":
            dd_id += dd_dict["id"] + "_"
            recipients.append(create_recipient(dd_dict))
        elif dd_dict["dd_type"].endswith("temporal"):
            dd_id += dd_dict["id"] + "_"
            storage_temporal.append(dd_dict)
        elif dd_dict["dd_type"].endswith("purposeConditional"):
            dd_id += dd_dict["id"] + "_"
            storage_purpose.append(dd_dict)
        elif dd_dict["dd_type"].endswith("legalBasisConditional"):
            dd_id += dd_dict["id"] + "_"
            storage_legal.append(dd_dict)
        else:
            raise ValueError("DataDisclosed type \"" + str(dd_dict["dd_type"]) + "\" is unknown.")
    dd_id = dd_id.rstrip("_")
    storage = create_storage_tilt(storage_temporal, storage_purpose, storage_legal)
    return tid_pb2.DataDisclosed(
        id=dd_id,
        category=category,
        purposes=purposes,
        legal_bases=legal_bases,
        recipients=recipients,
        storage=[storage]
    )


# searches for tags in datadisclosed property
def search_json_for_tag(tag):
    ti_dict = read_ti_dict()
    for key, value in ti_dict["dataDisclosed"].items():
        if type(value) is dict:
            for s_key, s_list in value.items():
                dd_type = key + ":" + s_key
                search_result = search_list_for_tag(s_list, tag, dd_type)
                if search_result is not None:
                    return search_result
        else:
            search_result = search_list_for_tag(value, tag, key)
            if search_result is not None:
                return search_result
    for key in ti_dict.keys():
        search_result = search_basic_types_for_id(tag, key)
        if search_result is not None:
            return search_result
    return None


def search_basic_types_for_id(ti_id, ti_type):
    ti_dict = read_ti_dict()
    if ti_type in ti_dict.keys():
        for item in ti_dict[ti_type]:
            if type(item) is dict and item["id"] == ti_id:
                item["ti_type"] = ti_type
                return item
    return None


def search_dict_for_tag(ti_dict, tag, dd_type):
    # if tag == "COA7_C1" and dd_type == "purposes": print("search_dict_for_tag:\n  dict: " + str(ti_dict) + "\n  tag: " + tag + "\n  type: " + dd_type)  # debugging
    if "id" not in ti_dict.keys():
        return search_list_for_tag(ti_dict.values(), tag, dd_type)
    elif ti_dict["id"] == tag:
        # print("if id in ti_dict.keys() and ti_dict[id] == tag")  # debugging
        ti_dict["dd_type"] = dd_type
        return ti_dict
    elif "child" in ti_dict.keys():
        return search_list_for_tag(ti_dict["child"], tag, dd_type)
    else:
        return None


def search_list_for_tag(ti_list, tag, dd_type):
    # if tag == "COA7_C1" and dd_type == "purposes": print("search_list_for_tag:\n  list: " + str(ti_list) + "\n  tag: " + tag + "\n  type: " + dd_type)  # debugging
    for value in ti_list:
        if type(value) is list:
            search_result = search_list_for_tag(value, tag, dd_type)
            if type(search_result) is dict:
                return search_result
        elif type(value) is dict:
            search_result = search_dict_for_tag(value, tag, dd_type)
            if type(search_result) is dict:
                return search_result
        else:
            raise TypeError("\"" + str(value) +
                            "\" is neither of class dict nor list but of type " + str(type(value)))
    return None


def read_ti_dict():
    dict_name = os.getenv("TI_DICTIONARY_NAME", "TransparencyInformationDictionary.json")
    with open("../dictionary/" + dict_name) as json_file:
        data = json.load(json_file)
        return data


# below the TIL Object is build
def create_purposes(purpose_list):
    result_list = []
    for i in range(len(purpose_list)):
        result_list.append(create_purpose(purpose_list[i]))
    return result_list


# child is getting elavated to a higher hierarchy level (therefore TIL Conform)
def create_purpose(attribute_dict):
    if "child" in attribute_dict:
        purpose = tid_pb2.Purpose(
            id=attribute_dict["id"],  # mandatory
            purpose=attribute_dict["purpose"],  # mandatory
            description=attribute_dict["description"],  # mandatory
            child=create_purposes(attribute_dict["child"])
        )
    else:  # normal TIl purpose structure (mapping)
        purpose = tid_pb2.Purpose(
            id=attribute_dict["id"],  # mandatory
            purpose=attribute_dict["purpose"],  # mandatory
            description=attribute_dict["description"]  # mandatory
        )
    return purpose


# property legal_base is built
def create_legal_base(attribute_dict) -> tid_pb2.LegalBase:
    legal_base = tid_pb2.LegalBase(
        reference=attribute_dict["id"],  # mandatory
        short_description=if_exists(attribute_dict, "shortDescription"),
        description=if_exists(attribute_dict, "description")
    )
    return legal_base


# Creation of recipient property depending on of "representative" already exists or not; adoption of id that is new to TIL schema
def create_recipient(attribute_dict) -> tid_pb2.Recipient:
    if "representative" in attribute_dict.keys():
        rep_dict = attribute_dict["representative"]
        representative = tid_pb2.Recipient.Representative(
            name=if_exists(rep_dict, "name"),
            email=if_exists(rep_dict, "email"),
            phone=if_exists(rep_dict, "phone")
        )
        recipient = tid_pb2.Recipient(
            id=attribute_dict["id"],  # mandatory
            name=if_exists(attribute_dict, "name"),
            division=if_exists(attribute_dict, "division"),
            address=if_exists(attribute_dict, "address"),
            country=if_exists(attribute_dict, "country"),
            representative=representative,
            category=attribute_dict["category"]  # mandatory
        )
    else:
        recipient = tid_pb2.Recipient(
            id=attribute_dict["id"],  # mandatory
            name=if_exists(attribute_dict, "name"),
            division=if_exists(attribute_dict, "division"),
            address=if_exists(attribute_dict, "address"),
            country=if_exists(attribute_dict, "country"),
            category=attribute_dict["category"]  # mandatory
        )
    return recipient


# Creation of the storage property
def create_storage(attribute_dict, storage_type) -> tid_pb2.Storage:
    if storage_type == "temporal":
        storage = tid_pb2.Storage(
            id=attribute_dict["id"],  # mandatory
            description=attribute_dict["description"],  # mandatory
            ttl=attribute_dict["ttl"],  # mandatory
            type=tid_pb2.Storage.TEMPORAL
        )
    elif storage_type == "purposeConditional":
        storage = tid_pb2.Storage(
            id=attribute_dict["id"],  # mandatory
            description=attribute_dict["description"],  # mandatory
            type=tid_pb2.Storage.PURPOSE,
        )
    elif storage_type == "legalBasisConditional":
        storage = tid_pb2.Storage(
            id=attribute_dict["id"],  # mandatory
            description=attribute_dict["description"],  # mandatory
            type=tid_pb2.Storage.LEGAL,
        )
    else:
        raise ValueError("Storage type \"" + storage_type + "\" is unknown.")
    return storage


# creation of the storage property that is more til conform which means taking away the granular id and description field (mapping description) as it does not exist in this way in TIl
def create_storage_tilt(temporals, purpose_conditionals, legal_conditionals,
                        aggregation=tid_pb2.MAX) -> tid_pb2.DataDisclosed.StorageTilt:
    tilt_temporals = []
    tilt_purposes = []
    tilt_legals = []
    for temporal in temporals:
        tilt_temporals.append(create_storage_temporal_tilt(temporal))
    for purpose in purpose_conditionals:
        tilt_purposes.append(purpose["description"])
    for legal in legal_conditionals:
        tilt_legals.append(legal["description"])
    return tid_pb2.DataDisclosed.StorageTilt(
        temporal=tilt_temporals,
        purposeConditional=tilt_purposes,
        legalBasisConditional=tilt_legals,
        aggregationFunction=aggregation
    )


def create_storage_temporal_tilt(attribute_dict) -> tid_pb2.DataDisclosed.StorageTilt.Temporal:
    temporal = tid_pb2.DataDisclosed.StorageTilt.Temporal(
        description=attribute_dict["description"],  # mandatory
        ttl=attribute_dict["ttl"]  # mandatory
    )
    return temporal


def if_exists(dictionary, key, default=""):
    if key in dictionary.keys():
        return dictionary[key]
    else:
        return default


class HealthCheck():
    def Check(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    tid_pb2_grpc.add_TIDictServicer_to_server(TIDService(), server)
    health_pb2_grpc.add_HealthServicer_to_server(TIDService(), server)
    port = port = os.getenv("TID_SERVICE_PORT", "50050")
    server.add_insecure_port("[::]:" + port)
    server.start()

    def handle_sigterm(*_):
        print("Received shutdown signal")
        all_rpcs_done_event = server.stop(30)
        all_rpcs_done_event.wait(30)
        print("Shut down gracefully")

    signal(SIGTERM, handle_sigterm)
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig()
    serve()
