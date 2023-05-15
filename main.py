from typing import Union
from fastapi import FastAPI, HTTPException, Request
import requests
from pydantic import BaseModel
import base64


URL="https://api.easee.cloud/api/"


# ==================== FastAPI ===================
# uvicorn main:app --host 161.35.205.84 --port 8000 --reload &
# http://161.35.205.84:8000/
#
# TODO
# Encryption and decryption of passwords
# OK -- GET : User and Charger Specific Consumption : https://developer.easee.cloud/reference/get_api-sessions-charger-chargerid-sessions-from-to
# POST : Set Dynanic Circuit Current : https://developer.easee.cloud/reference/post_api-sites-siteid-circuits-circuitid-dynamiccurrent
# 
#
# ==============API STATUS CODES==================
# 409 : Max Charger Current Is Reached
# 200 : OK, data returned succesfully
# 500 : Internal Server Error in this API
# 502 : When trying too many times, wait a couple of minutes and try again the endpoint -> Bad Gateway
# 403 : You don’t have privileges to use this endpoint -> Forbidden
# 401 : Token was not accepted or need to do authentication again -> UnAuthorized
# 202 : Your command was accepted but may not have made a change or impact on the device yet, please follow up with a status check or observation call -> Accepted
# ================================================

app = FastAPI()


# Decode Base64 passwords that are given in Loxone
def decode_pwd(pwd_base64:str):
    decoded_bytes = base64.b64decode(pwd_base64)
    decoded_string = decoded_bytes.decode('utf-8')
    return decoded_string

# Returns the bearer token when credential (username & password) are valid
def get_bearer_token(username: str, password: str):
    decoded_pwd = decode_pwd(password)
    url = f"{URL}accounts/login"
    headers = { "Content-Type": "application/json" }
    data = { "userName": username,"password": decoded_pwd }
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        bearer_token = response_data.get("accessToken")
        return bearer_token
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


# Generel request function that requests GET with the valid URL to the Easee API
def get_request(url:str, username:str, password:str):
    token = get_bearer_token(username, password)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"Easee Api Gateway - docs": "http://161.35.205.84:8000/docs#/"}


# Returns the configuration of the given chargerId, needs verification in order to retreive data : https://developer.easee.cloud/reference/get_api-chargers-id-config
@app.get("/getConfiguration/{chargerId}/{username}/{password}")
def get_configuration_old(chargerId:str, username:str, password:str):  
    response = get_request(f"{URL}chargers/{chargerId}/config", username, password)
    return response

# Returns the state of the given chargerId, needs verification in order to retreive data : https://developer.easee.cloud/reference/get_api-chargers-id-state
@app.get("/state/{chargerId}/{username}/{password}")
def get_state(chargerId:str, username:str, password:str):  
    response = get_request(f"{URL}chargers/{chargerId}/state", username, password)
    return response

# Returns the powerusage between 2 time slots -> parameters need to be URL encoded in order to retreive data, needs verification in order to retreive data : https://developer.easee.cloud/reference/get_api-chargers-id-usage-hourly-from-to
@app.get("/powerUsage/{chargerId}/{afrom}/{to}/{username}/{password}")
def get_power_usage(chargerId:str, afrom:str, to:str, username:str, password:str):  
    response = get_request(f"{URL}chargers/{chargerId}/usage/hourly/{afrom}/{to}", username, password)
    return response

# Return the charger details of the given chargerId, needs verification in order to retreive data : https://developer.easee.cloud/reference/get_api-chargers-id-details
@app.get("/getChargerDetails/{chargerId}/{username}/{password}")
def get_charger_details(chargerId:str, username:str, password:str):  
    response = get_request(f"{URL}chargers/{chargerId}/details", username, password)
    return response

# Returns the same JSON as /getConfiguration but with an extra field in the JSON where 'isEnabled' is altered from True/False to 1/0 : https://developer.easee.cloud/reference/get_api-chargers-id-config
@app.get("/getIsEnabled/{chargerId}/{username}/{password}") 
def get_is_enabled(chargerId:str, username:str, password:str):  
    jsonData = get_request(f"{URL}chargers/{chargerId}/config", username, password)
    jsonData['isEnabledDigital'] = 1 if jsonData['isEnabled'] else 0 
    return jsonData

# GET : User and Charger Specific Consumption : https://developer.easee.cloud/reference/get_api-sessions-charger-chargerid-sessions-from-to * Encode URL
@app.get("/getChargingSessions/{chargerId}/{afrom}/{to}/{username}/{password}")
def get_charging_sessions(chargerId:str, afrom:str, to:str, username:str, password:str):
    response = get_request(f"{URL}sessions/charger/{chargerId}/sessions/{afrom}/{to}", username, password)
    return response

# Returns all the sites that are configured on the user's account
@app.get("/getSites/{username}/{password}")
def get_sites(username:str, password:str):
    response = get_request(f"{URL}sites", username, password)
    return response

# In development, unsure what circuitId is in order to perform the POST request -> https://developer.easee.cloud/reference/post_api-sites-siteid-circuits-circuitid-dynamiccurrent
@app.get("/isCircuitAttached/{siteId}/{serialNumber}/{pinCode}/{username}/{password}")
def is_circuit_attached(siteId:str, serialNumber:str, pinCode:str, username:str, password:str):
    response = get_request(f"{URL}sites/{siteId}/circuits/{serialNumber}/{pinCode}", username, password)
    return response

# Schema
class LedstripBrightnessRequest(BaseModel):
    username: str
    password: str
    brightness: int
    chargerId: str

# POST request to the Easee API where you can change the leddstrip brightness, interval -> 0-100
@app.post("/setLedstripBrightness")
def set_ledstrip_brightness(request: Request, ledstrip_brightness: LedstripBrightnessRequest):
    username = ledstrip_brightness.username
    password = ledstrip_brightness.password
    brightness = ledstrip_brightness.brightness
    charger_id = ledstrip_brightness.chargerId
    token = get_bearer_token(username, password)
    url = f"{URL}chargers/{charger_id}/settings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = { "ledStripBrightness": brightness }
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e)) 

# Schema
class SetIsEnabledRequest(BaseModel):
    username: str
    password: str
    enabled: bool
    chargerId: str


# Change the 'isEnabled' to True or false, given parameters is 0/1 or true/false : https://developer.easee.cloud/reference/post_api-chargers-id-settings
@app.post("/setIsEnabled")
def set_is_enabled(request: Request, set_is_enabled: SetIsEnabledRequest):
    username = set_is_enabled.username
    password = set_is_enabled.password
    is_enabled = set_is_enabled.enabled
    charger_id = set_is_enabled.chargerId
    token = get_bearer_token(username, password)
    url = f"{URL}chargers/{charger_id}/settings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = { "enabled": is_enabled }
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


# Schema
class SetDynamicChargerCurrentRequest(BaseModel):
    username: str
    password: str
    dynamicChargerCurrent: float
    chargerId: str

# Set dynamix charger current -> POST request, parameter of dynamicChargerCurrent is given as a float : https://developer.easee.cloud/reference/post_api-chargers-id-settings
@app.post("/setDynamicChargerCurrent")
def set_dynamic_charger_current(request: Request, set_dynamic_charger_current: SetDynamicChargerCurrentRequest):
    username = set_dynamic_charger_current.username
    password = set_dynamic_charger_current.password
    dynamic_charger_current = set_dynamic_charger_current.dynamicChargerCurrent
    charger_id = set_dynamic_charger_current.chargerId
    token = get_bearer_token(username, password)
    url = f"{URL}chargers/{charger_id}/settings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = { "dynamicChargerCurrent": dynamic_charger_current }
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# Schema
class SetMaxChargerCurrentRequest(BaseModel):
    username: str
    password: str
    maxChargerCurrent: float
    chargerId: str
    maxChargerAccepted: float

# Check if max allowed charger current is reached : if reached the post request wont happen 
def check_max_allowed_charger_current(max_charger_current_accepted:float, max_charger_current:float):
    return max_charger_current_accepted>=max_charger_current

# Set MaxChargerCurrent, POST request to Easee api to update the 'maxChargerCurrent': https://developer.easee.cloud/reference/post_api-chargers-id-settings
@app.post("/setMaxChargerCurrent")
def set_max_charger_current(request: Request, set_max_charger_current: SetMaxChargerCurrentRequest):
    username = set_max_charger_current.username
    password = set_max_charger_current.password
    max_charger_current = set_max_charger_current.maxChargerCurrent
    charger_id = set_max_charger_current.chargerId
    max_charger_current_accepted = set_max_charger_current.maxChargerAccepted
    token = get_bearer_token(username, password)
    url = f"{URL}chargers/{charger_id}/settings"
    if(check_max_allowed_charger_current(max_charger_current_accepted, max_charger_current)):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = { "maxChargerCurrent": max_charger_current }
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=409, detail="Max allowed Charger Current reached... Abort")

# POST -> Set Dynamic Circuit Current : https://developer.easee.cloud/reference/post_api-sites-siteid-circuits-circuitid-dynamiccurrent