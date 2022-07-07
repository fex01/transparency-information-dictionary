import unittest
from pprint import pprint

import tid_pb2
import tid_pb2_grpc
import grpc

tid_host = "localhost"
tid_port = "50050"
tid_channel = grpc.insecure_channel(
    f"{tid_host}:{tid_port}"
)
tid_server = tid_pb2_grpc.TIDictStub(tid_channel)


class TestTIDictService(unittest.TestCase):

    def test_invalid_keyvalue(self):
        response = tid_server.GetDataDisclosedOfType(
            tid_pb2.DataDisclosedRequest(value=17), None
        )
        assert response.list[0].null_value == tid_pb2.NULL_VALUE

    def test_category(self):
        response = tid_server.GetDataDisclosedOfType(
            tid_pb2.DataDisclosedRequest(value=tid_pb2.CATEGORY), None
        )
        assert response.list[0].category.id == "C01"

    def test_purpose(self):
        response = tid_server.GetDataDisclosedOfType(
            tid_pb2.DataDisclosedRequest(value=tid_pb2.PURPOSE), None
        )
        assert response.list[0].purpose.id == "DATA1"
        assert response.list[0].purpose.child[0].id == "DATA1_IS1"

    def test_legal(self):
        response = tid_server.GetDataDisclosedOfType(
            tid_pb2.DataDisclosedRequest(value=tid_pb2.LEGAL_BASE), None
        )
        assert response.list[0].legal_base.reference == "GDPR-13-1-a"

    def test_recipient(self):
        response = tid_server.GetDataDisclosedOfType(
            tid_pb2.DataDisclosedRequest(value=tid_pb2.RECIPIENT), None
        )
        print(response.list)
        assert response.list[0].recipient.id == "R01"
        assert response.list[0].recipient.representative.name == "Jane Super"

    def test_recipient_missing_values(self):
        response = tid_server.GetDataDisclosedOfType(
            tid_pb2.DataDisclosedRequest(value=tid_pb2.RECIPIENT), None
        )
        assert response.list[2].recipient.id == "R03"
        assert response.list[2].recipient.country == ""

    def test_storage(self):
        response = tid_server.GetDataDisclosedOfType(
            tid_pb2.DataDisclosedRequest(value=tid_pb2.STORAGE), None
        )
        assert response.list[0].storage.id == "ST01"
        assert response.list[0].storage.type == tid_pb2.Storage.TEMPORAL
        assert response.list[11].storage.id == "SPC01"
        assert response.list[11].storage.type == tid_pb2.Storage.PURPOSE
        assert response.list[21].storage.id == "SL01"
        assert response.list[21].storage.type == tid_pb2.Storage.LEGAL

    def test_third_country_transfer(self):
        response = tid_server.GetThirdCountryTransfers(tid_pb2.TCTRequest(), None)
        assert response.third_country_transfers[1].id == "TCT02"
        assert response.third_country_transfers[1].adequacy_decision.available
        assert response.third_country_transfers[1].appropriate_guarantees.available
        assert response.third_country_transfers[1].presence_of_enforceable_rights_and_effective_remedies.available
        assert response.third_country_transfers[1].standard_data_protection_clause.available

    def test_change_of_purpose(self):
        response = tid_server.GetChangesOfPurpose(tid_pb2.COPRequest(), None)
        assert response.changes_of_purposes[0].id == "COP01"
        assert response.changes_of_purposes[0].affected_data_categories[0].value == "E-mail address"

    def test_tags_2_data_disclosed(self):
        response = tid_server.GetTransparencyInformationFromTagList(
            tid_pb2.TagListRequest(tags="[C01, R02, ST11]"), None
        )
        assert response.data_disclosed.id == "C01_R02_ST11"
        assert response.data_disclosed.category == "E-mail address"
        assert response.data_disclosed.storage[0].temporal[0].description == "Live data - log detention time."

    def test_tags_2_third_country_transfer(self):
        response = tid_server.GetTransparencyInformationFromTagList(
            tid_pb2.TagListRequest(tags="[TCT02]"), None
        )
        assert response.HasField("third_country_transfer")
        assert response.third_country_transfer.id == "TCT02"
        assert response.third_country_transfer.adequacy_decision.available
        assert response.third_country_transfer.appropriate_guarantees.available
        assert response.third_country_transfer.presence_of_enforceable_rights_and_effective_remedies.available
        assert response.third_country_transfer.standard_data_protection_clause.available

    def test_tags_2_change_of_purpose(self):
        response = tid_server.GetTransparencyInformationFromTagList(
            tid_pb2.TagListRequest(tags="[COP01]"), None
        )
        assert response.change_of_purpose.id == "COP01"
        assert response.change_of_purpose.affected_data_categories[0].value == "E-mail address"

    def test_get_ti_from_traces(self):
        response = tid_server.GetTransparencyInformationFromTraces(
            tid_pb2.TransparencyInformationRequest(cover_traces_of_the_last_x_min=30), None
        )
        # pprint(response)
        for item in response.services:
            if item.service == "emailservice":
                emailservice = item
        pprint(emailservice)
        assert emailservice.service == "emailservice"
        assert emailservice.data_disclosed_entries[0].id == "C01_R02_COA7_C1_ST11"
        assert emailservice.data_disclosed_entries[0].category == "E-mail address"


if __name__ == '__main__':
    unittest.main()
