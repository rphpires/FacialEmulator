# -*- coding: utf-8 -*-

#
# W-Access REST API access client example
#
# Tested with Python 2.7.15 and 3.7.4. Requires "requests" library (http://docs.python-requests.org/en/latest/)
#
# To install requests, you need to run "pip.exe install requests"
#
# In windows, you may need to run the following commands to change the command prompt encoding to utf-8
#   chcp 65001
#   set PYTHONIOENCODING=UTF-8
#
# http://localhost/W-AccessAPI/swagger/ can be accessed for complete documentation, and to call
# methods individually for testing porpouses. For this URL to work, a default user / passwd has to
# be specified in W-AccessAPI/Web.config <appSettings> section. For example:
# <add key="DefaultWAccessAuthentication" value="admin:#admin#" />
# It is recomended to disable this default user configuration when the system enters production stage
#
# The API always replies with one of the following HTTP reponse codes:
# * On success:
# 200 - OK (successful GET operation)
# 201 - Created (successful POST operation)
# 204 - No content (successful DELETE or PUT operation)
# * On errors (check "Message" JSON field in reposne body for additional information)
# 400 - Bad request (some error occured. "ModelState" JSON field may be set, in case of model validation errors)
# 404 - Not found (entity not found)
#
# Currently, error codes 5xx (Server error) are not returned by the API. Bad requests errors are returned instead,
# and the "Message" field should help to identify if the error happened due to a system problem.
#
# An additional optional parameter, "fields" is globally supported. It defines which data items should be
# returned by the calls. This is useful when a large amount of data is being retrieved, and the amount of used
# bandwidth is to be reduced. As an example, the events fetching call presented bellow uses this parameter.
#


import requests, json, traceback, sys, base64

try:

    #url = "http://192.168.1.106:80/W-AccessAPI/v1/"
    url = "http://localhost/W-AccessAPI/v1/"

    h = { 'WAccessAuthentication': 'WAccessAPI:#WAccessAPI#', 'WAccessUtcOffset': '-180' }

    print("\n* Cardholders - Get by IdNumber")
    cardholder = None
    reply = requests.get(url + 'cardholders', headers=h, params = (("IdNumber", u"555666"),))
    reply_json = reply.json()
    
    ## Version 4.205 or older
    try:
        if reply.status_code == requests.codes.ok:
            print("Found Cardholder: Name=%s"%(reply_json["FirstName"]))
            cardholder = reply_json
        elif reply.status_code == requests.codes.not_found:
            print("Cardholder not found")
        else:
            print("Error: " + reply_json["Message"])
    ## Version 4.206 or newer
    except:
        for wxs_user in reply_json:
            if reply.status_code == requests.codes.ok:
                print("Found Cardholder: Name=%s"%(wxs_user["FirstName"]))
                cardholder = wxs_user
            

    if not cardholder:
        print("\n* Cardholders - Create")
        new_cardholder = { "FirstName": u"José Funcionário", "CHType": 2, "IdNumber": u"555666", "PartitionID": 1}
        reply = requests.post(url + 'cardholders', json=new_cardholder, headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.created:
            print("New CHID: %d"%(reply_json["CHID"]))
            cardholder = reply_json
        else:
            print("Error: " + reply_json["Message"])
            if "ModelState" in reply_json.keys():
                for field_name in reply_json["ModelState"].keys():
                    print("%s: %s"%(field_name, ";".join(reply_json["ModelState"][field_name])))

    if not cardholder:
        sys.exit(1)

    print("\n* Cardholders - Update")
    cardholder["FirstName"] = u"João Funcionário"
    reply = requests.put(url + 'cardholders', json=cardholder, headers=h)
    if reply.status_code == requests.codes.no_content:
        print("Cardholder update OK")
    else:
        print("Error: " + reply.json()["Message"])
        

    print("\n* Cardholders - Set photo 1")
    f = open("photo1.jpg", "rb")
    data = f.read()
    f.close()
    reply = requests.put(url + 'cardholders/%d/photos/1'%(cardholder["CHID"]), files=(('photoJpegData', data), ), headers=h)
    if reply.status_code in [ requests.codes.ok, requests.codes.no_content ]:
        print("Cardholder photo 1 update OK")
    else:
        print("Error: " + str(reply))


    print("\n* Cardholders - Set photo 2")
    f = open("photo2.jpg", "rb")
    data = f.read()
    f.close()
    reply = requests.put(url + 'cardholders/%d/photos/2'%(cardholder["CHID"]), files=(('photoJpegData', data), ), headers=h)
    if reply.status_code in [ requests.codes.ok, requests.codes.no_content ]:
        print("Cardholder photo 2 update OK")
    else:
        print("Error: " + str(reply))

    print("\n* Cardholders - Get photo 1")
    reply = requests.get(url + 'cardholders/%d/photos/2'%(cardholder["CHID"]), headers=h)
    if reply.status_code == requests.codes.ok:
        print("Found Cardholder photo")
        f = open("photo1_get.jpg", "wb")
        f.write(base64.b64decode(reply.json()))
        f.close()
        
    elif reply.status_code == requests.codes.not_found:
        print("Cardholder not found")
    else:
        print("Error: " + reply_json["Message"])

    
    print("\n* Cardholders - Set fingerprint 3")
    f = open("fingerprint_3.bmp", "rb")
    data = f.read()
    f.close()
    data64 = base64.b64encode(data).decode("utf-8")
    fingerprint = { 'FingerprintImage': data64, 'IsDuress': False }
    reply = requests.put(url + 'cardholders/%d/fingerprints/3'%(cardholder["CHID"]), json=fingerprint, headers=h)
    if reply.status_code == requests.codes.no_content:
        print("Cardholder fingerprint 3 update OK")
    else:
        print("Error: " + reply.json()["Message"])
    

    print("\n* Cardholders - Set fingerprint 5")
    f = open("fingerprint_5.bmp", "rb")
    data = f.read();
    f.close()
    data64 = base64.b64encode(data).decode("utf-8")
    fingerprint = { 'FingerprintImage': data64, 'IsDuress': False }
    reply = requests.put(url + 'cardholders/%d/fingerprints/5'%(cardholder["CHID"]), json=fingerprint, headers=h)
    if reply.status_code == requests.codes.no_content:
        print("Cardholder fingerprint 5 update OK")
    else:
        print("Error: " + reply.json()["Message"])

    print("\n* Cardholders - Get fingerprints")
    reply = requests.get(url + 'cardholders/%d/fingerprints'%(cardholder["CHID"]), headers=h)
    reply_json = reply.json()
    if reply.status_code == requests.codes.ok:
        print("\n* Found cardholder %s fingerprints."%(len(reply_json)))
        for fingerprint in reply_json:
            f = open("fingerprint_%d_get.bmp"%(fingerprint['FingerIndex']), "wb")
            f.write(base64.b64decode(fingerprint['FingerprintImage']))
            f.close()
        
    elif reply.status_code == requests.codes.not_found:
        print("Card not found")
    else:
        print("Error: " + reply_json["Message"])
    

    print("\n* Cardholders - Delete fingerprint 5")
    #reply = requests.delete(url + 'cardholders/%d/fingerprints/5'%(cardholder["CHID"]), headers=h)
    #if reply.status_code == requests.codes.no_content:
        #print("Cardholder fingerprint 5 delete OK")
    #else:
        #print("Error: " + reply.json()["Message"])


    print("\n* Card - Get by ClearCode")
    card = None
    reply = requests.get(url + 'cards', headers=h, params = (("ClearCode", u"ABC_12345"),))
    reply_json = reply.json()
    ## Version 4.205 or older
    try:
        if reply.status_code == requests.codes.ok:
            print("\n* Found Card: %s %s"%(reply_json["CardID"], reply_json["CardEndValidityDateTime"]))
            card = reply_json
        elif reply.status_code == requests.codes.not_found:
            print("Card not found")
        else:
            print("Error: " + reply_json["Message"])
    ## Version 4.206 or newer
    except:
        for wxs_card in reply_json:
            if reply.status_code == requests.codes.ok:
                print("\n* Found Card: %s %s"%(wxs_card["CardID"], wxs_card["CardEndValidityDateTime"]))
                card = wxs_card
            elif reply.status_code == requests.codes.not_found:
                print("Card not found")
            else:
                print("Error: " + wxs_card["Message"])


    if card and card["CHID"]:
        print("\n* Card is assigned. Unassigning it")
        reply = requests.delete(url + 'cardholders/%d/cards/%d'%(card["CHID"], card["CardID"]), json=card, headers=h)
        if reply.status_code == requests.codes.no_content:
            print("Card unassigned")
        elif reply.status_code == requests.codes.not_found:
            print("Card not found for unassign")
        else:
            print("Error: " + reply.json()["Message"])


    if card:
        print("\n* Card - Delete")
        reply = requests.delete(url + 'cards', headers=h, params = (("ClearCode", u"ABC_12345"),))
        if reply.status_code == requests.codes.no_content:
            print("Card Deleted")
        elif reply.status_code == requests.codes.not_found:
            print("Card not found for deletion")
        else:
            reply_json = reply.json()
            print("Error: " + reply.json()["Message"])
        card = None


    if not card:
        print("\n* Card - Create resident card (CardType = 0)")
        new_card = { "ClearCode": u"ABC_12345", "CardNumber": 12345, "PartitionID": 0, "CardType" : 0 }
        reply = requests.post(url + 'cards', json=new_card, headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.created:
            card = reply_json
            print("New CardID: %d"%(card["CardID"]))
        else:
            print("Error: " + reply_json["Message"])


    if card:
        print("\n* Card - Assign to Cardholder")
        #card["CardEndValidityDateTime"] = "2016-01-01T10:00:00"
        reply = requests.post(url + 'cardholders/%d/cards'%(cardholder["CHID"]), json=card, headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.created:
            card = reply_json
            print("Card assigned")
            print("%s %s"%(card["CardID"], card["CardEndValidityDateTime"]))
        else:
            print("Error: " + reply_json["Message"])


    # AccessLevels - Get All Access Levels
    reply = requests.get(url + 'accessLevels', headers=h, params=(("fields", "AccessLevelID,AccessLevelName"),))
    reply_json = reply.json()
    if reply.status_code == requests.codes.ok:
        print("\n* AccessLevels:")
        for access_level in reply_json:
            print("ID=%d, Name=%s"%(access_level["AccessLevelID"], access_level["AccessLevelName"]))
    else:
        print("Error: " + reply_json["Message"])


    print("\n* CHAccessLevels - List Cardholder's AccessLevels IDs")
    ch_access_levels = []
    reply = requests.get(url + 'cardholders/%d/accessLevels'%(cardholder["CHID"]), headers=h)
    reply_json = reply.json()
    if reply.status_code == requests.codes.ok:
        ch_access_levels = reply_json
        print("Current AccessLevels IDs Assigned to %s:"%(cardholder["FirstName"]))
        for ch_access_level in ch_access_levels:
            print("ID=%d"%(ch_access_level["AccessLevelID"]))
    else:
        print("Error: " + reply_json["Message"])


    print("\n* CHAccessLevels - Unassign all AccessLevels from Cardholder")
    for ch_access_level in ch_access_levels:
        reply = requests.delete(url + 'cardholders/%d/accessLevels/%d'%(cardholder["CHID"], ch_access_level["AccessLevelID"]), headers=h)
        if reply.status_code == requests.codes.no_content:
            print("Unassigned AccessLevelsID %d from %s:"%(ch_access_level["AccessLevelID"],cardholder["FirstName"]))
        else:
            print("Error: " + reply.json()["Message"])


    print("\n* AccessLevels - Get Access Level by Name")
    access_level = None
    reply = requests.get(url + 'accessLevels', headers=h, params=(("AccessLevelName", "Total"),))
    access_level = reply.json()
    ## Version 4.205 or older
    try:
        if reply.status_code == requests.codes.ok:
            print("AccessLevel 'Total' Found: ID=%d, Name=%s"%(access_level["AccessLevelID"], access_level["AccessLevelName"]))
        elif reply.status_code == requests.codes.not_found:
            print("Access Level 'Total' not found")
        else:
            print("Error: " + reply.json()["Message"])
    ## Version 4.206 or newer
    except:
        for ac in access_level:
            if reply.status_code == requests.codes.ok:
                print("AccessLevel 'Total' Found: ID=%d, Name=%s"%(ac["AccessLevelID"], ac["AccessLevelName"]))
            elif reply.status_code == requests.codes.not_found:
                print("Access Level 'Total' not found")


    if not access_level:
        print("\n* AccessLevel - Create AccessLevel 'Total'")
        new_access_level = { "AccessLevelName": "Total", "LocalityID": 1, "PartitionID": 0 }
        reply = requests.post(url + 'accessLevels', json=new_access_level, headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.created:
            access_level = reply_json
            print("New AccessLevelID: %d"%(access_level["AccessLevelID"]))
        else:
            print("Error: " + reply_json["Message"])

    if access_level:
        print("\n* CHAccessLevels - Assign AccessLevel 'Total' to CH")
        reply = requests.post(url + 'cardholders/%d/accesslevels/%d'%(cardholder["CHID"],ac["AccessLevelID"]), headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.created:
            ch_access_level = reply_json
            print("Access Level 'Total' assigned")
            print("CHID=%d AccessLevelID=%d"%(ch_access_level["CHID"], ch_access_level["AccessLevelID"]))
        else:
            print("Error: " + reply_json["Message"])


    print("\n* Events - Show events since a given date (up to 50)")
    reply = requests.get(url + 'events', headers=h, params=(("offset", 0), ("limit", 50), ("minEventDateTime", "2015-01-01T00:00:00"), ("fields", "EventDateTime,EventType,EventHWID,SourceName,SourceValue")))
    if reply.status_code == requests.codes.ok:
        events = reply.json()
        print("Events:")
        for event in events:
            print("%s %s %s %s %s"%(event["EventDateTime"], event["EventType"], event["EventHWID"], event["SourceName"], event["SourceValue"]))
    else:
        print("Error: " + reply.json()["Message"])


    # Visits
    print("\n\n** Visits testing")
    print("\n* Cardholders - Get by IdNumber")

    # original cardholder will be uysed later as contact for visitor
    cardholder_contact = cardholder

    cardholder = None
    reply = requests.get(url + 'cardholders', headers=h, params = (("IdNumber", u"555777"),))
    reply_json = reply.json()
    ## Version 4.205 or older
    try:
        if reply.status_code == requests.codes.ok:
            print("Found Cardholder Name=%s"%(reply_json["FirstName"]))
            cardholder = reply_json
        elif reply.status_code == requests.codes.not_found:
            print("Cardholder not found")
        else:
            print("Error: " + reply_json["Message"])
    ## Version 4.206 or newer
    except:
        for wxs_user in reply_json:
            if reply.status_code == requests.codes.ok:
                print("Found Cardholder Name=%s"%(wxs_user["FirstName"]))
                cardholder = wxs_user
            elif reply.status_code == requests.codes.not_found:
                print("Cardholder not found")
            else:
                print("Error: " + wxs_user["Message"])

    if not cardholder:
        print("\n* Cardholders - Create visitor (CHType = 1)")
        new_cardholder = { "FirstName": u"João Visitante", "CHType": 1, "IdNumber": u"555777", "PartitionID": 1}
        # new_cardholder = { "FirstName": u"João Visitante", "CHType": 0, "IdNumber": u"555777", "PartitionID": 1}
        reply = requests.post(url + 'cardholders', json=new_cardholder, headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.created:
            print("New CHID=%d"%(reply_json["CHID"]))
            cardholder = reply_json
        else:
            print("Error: " + reply_json["Message"])
            if "ModelState" in reply_json.keys():
                for field_name in reply_json["ModelState"].keys():
                    print("%s: %s"%(field_name, ";".join(reply_json["ModelState"][field_name])))

    print("\n* Card - Get by ClearCode")
    card = None
    reply = requests.get(url + 'cards', headers=h, params = (("ClearCode", u"VISITOR_1234567"),))
    reply_json = reply.json()
    ## Version 4.205 or older
    try:
        if reply.status_code == requests.codes.ok:
            reply_json = reply.json()
            print("Found CardID=%d"%(reply_json["CardID"]))
            card = reply.json()
        elif reply.status_code == requests.codes.not_found:
            print("Card not found")
        else:
            reply_json = reply.json()
            print("Error: " + reply.json()["Message"])
    ## Version 4.206 or newer
    except:
        for wxs_card in reply_json:
            if reply.status_code == requests.codes.ok:
                print("Found CardID=%d"%(wxs_card["CardID"]))
                card = reply.json()
            elif reply.status_code == requests.codes.not_found:
                print("Card not found")
            else:
                reply_json = reply.json()
                print("Error: " + reply.json()["Message"])


    if not card:
        print("\n* Card - Create visitor card (CardType = 1)")
        new_card = { "ClearCode": u"VISITOR_1234567", "CardNumber": 1234567, "PartitionID": 0, "CardType" : 1 }
        reply = requests.post(url + 'cards', json=new_card, headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.created:
            card = reply_json
            print("New CardID: %d"%(card["CardID"]))
        else:
            print("Error: " + reply_json["Message"])


    active_visit = None
    if cardholder:
        print("\n* Visit - Check if cardholder has a started visit")
        reply = requests.get(url + 'cardholders/%d/activeVisit'%(cardholder["CHID"]), headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.ok:
            active_visit = reply_json
            if active_visit:
                print("%s has an active visit. VisitStart=%s"%(cardholder["FirstName"], active_visit["VisitStart"]))
            else:
                print("%s has no active visit"%(cardholder["FirstName"]))
        else:
            print("Error: " + reply_json["Message"])


    if active_visit:
        print("\n* Visit - End current visit")
        reply = requests.delete(url + 'cardholders/%d/activeVisit'%(cardholder["CHID"]), headers=h)
        if reply.status_code == requests.codes.no_content:
            print("Visit ended")
        else:
            print("Error: " + reply.json()["Message"])


    if card and cardholder:
        print("\n* Visit - Start a new visit")
        new_visit = { "ClearCode": card["ClearCode"], "ContactCHID": cardholder_contact["CHID"] }
        reply = requests.post(url + 'cardholders/%d/activeVisit'%(cardholder["CHID"]), json=new_visit, headers=h)
        reply_json = reply.json()
        if reply.status_code == requests.codes.created:
            card = reply_json
            print("New Visit started")
        else:
            print("Error: " + reply_json["Message"])

except Exception as ex:
    print(ex)
    traceback.print_exc(file=sys.stdout)

#sys.stdin.readline()

# Cardholder model reference
##    {
##      "CHID": 0,
##      "CHType": 0,
##      "FirstName": "",
##      "LastName": "",
##      "CompanyID": 0,
##      "VisitorCompany": "",
##      "EMail": "",
##      "CHState": 0,
##      "IsUndesirable": False,
##      "IsUndesirableReason1": "",
##      "IsUndesirableReason2": "",
##      "PartitionID": 0,
##      "LastModifOnLocality": 0,
##      "LastModifDateTime": "",
##      "LastModifBy": "",
##      "CHStartValidityDateTime": "",
##      "CHEndValidityDateTime": "",
##      "CHDownloadRequired": False,
##      "TraceCH": False,
##      "Trace_AlmP": 0,
##      "Trace_Act": 0,
##      "TrustedLogin": "",
##      "DefFrontCardLayout": 0,
##      "DefBackCardLayout": 0,
##      "IdNumber": "",
##      "MaxTransits": 0,
##      "MaxMeals": 0,
##      "IgnoreTransitsCount": False,
##      "IgnoreMealsCount": False,
##      "IgnoreAntiPassback": False,
##      "IgnoreZoneCount": False,
##      "PIN": "",
##      "RequiresEscort": False,
##      "CanEscort": False,
##      "CanReceiveVisits": False,
##      "SubZoneID": 0,
##      "IgnoreRandomInspection": False,
##      "CHFloor": "",
##      "BdccState": 0,
##      "BdccIgnore": False,
##      "BdccCompanies": "",
##      "IdNumberType": 0,
##      "AuxText01": "",
##      "AuxText02": "",
##      "AuxText03": "",
##      "AuxText04": "",
##      "AuxText05": "",
##      "AuxText06": "",
##      "AuxText07": "",
##      "AuxText08": "",
##      "AuxText09": "",
##      "AuxText10": "",
##      "AuxText11": "",
##      "AuxText12": "",
##      "AuxText13": "",
##      "AuxText14": "",
##      "AuxText15": "",
##      "AuxTextA01": "",
##      "AuxTextA02": "",
##      "AuxTextA03": "",
##      "AuxTextA04": "",
##      "AuxTextA05": "",
##      "AuxLst01": 0,
##      "AuxLst02": 0,
##      "AuxLst03": 0,
##      "AuxLst04": 0,
##      "AuxLst05": 0,
##      "AuxLst06": 0,
##      "AuxLst07": 0,
##      "AuxLst08": 0,
##      "AuxLst09": 0,
##      "AuxLst10": 0,
##      "AuxLst11": 0,
##      "AuxLst12": 0,
##      "AuxLst13": 0,
##      "AuxLst14": 0,
##      "AuxLst15": 0,
##      "AuxChk01": False,
##      "AuxChk02": False,
##      "AuxChk03": False,
##      "AuxChk04": False,
##      "AuxChk05": False,
##      "AuxChk06": False,
##      "AuxChk07": False,
##      "AuxChk08": False,
##      "AuxChk09": False,
##      "AuxChk10": False,
##      "AuxDte01": "",
##      "AuxDte02": "",
##      "AuxDte03": "",
##      "AuxDte04": "",
##      "AuxDte05": "",
##      "AuxDte06": "",
##      "AuxDte07": "",
##      "AuxDte08": "",
##      "AuxDte09": "",
##      "AuxDte10": ""
##    }

