import cmd
import argparse
import requests
import json
import asyncio
import time
import os

import okta.models as models
from okta.client import Client as OktaClient

loop = asyncio.get_event_loop()

oktaOrgUrl = None
clientId = None
client = OktaClient()


def create_parser():
    parser = argparse.ArgumentParser(description="Okta Command Line Interface")

    parser.add_argument('-l', '--login', metavar="", help='Log into your Okta org; specify your org URL', required=False)
    parser.add_argument('-c', '--clientId', metavar="", help="OIDC client ID for CLI app; specify valid client ID", required=False)
    parser.add_argument('-r', '--register', metavar="", help="Register for an Okta Developer org; specify your "
                                                             "developer email address", required=False)
    return parser


class OktaCLI(cmd.Cmd):
    prompt = '>>'
    intro = 'Welcome to the Okta CLI. Type \'help\' for available commands'

    def do_list(self, line):
        """List objects in your org; valid options are users, groups, or apps"""

        async def run():
            if line == "user all":
                query_parameters = {'limit': '200'}
                users, resp, err = await client.list_users(query_parameters)

                list_users = True
                while list_users:
                    for user in users:
                        print(user.profile.first_name, user.profile.last_name + " - " + user.profile.login + " - " + user.id)

                    if resp.has_next():
                        users, err = await resp.next()
                    else:
                        print("")
                        list_users = False

            elif "user" in line:
                x = line.split()
                user, resp, err = await client.get_user(x[1])

                if user is not None:
                    print(f"User information for {user.profile.firstName} {user.profile.lastName}")
                    print("---")
                    print(f"ID: {user.id} | Status: {user.status}")
                    print("")

                    attribute = vars(user.profile)

                    for a in attribute:
                        value = getattr(user.profile, a)
                        if value is not None:
                            print(f"{a}: {value}")

                    print("")
                else:
                    print(err)
                    print("")

            elif line == "app":
                print("apps")
            elif line == "group":
                print("groups")
            else:
                print("Please specify what objects you would like to create.")
                print("Valid options are 'user', 'group', or 'app'\n")

        asyncio.run(run())

    def do_create(self, line):
        """Create objects in your org; valid options are user, group, or app"""

        async def run():
            if line == "user":
                schema, resp, error = await client.get_user_schema("default")

                # default attributes
                default = {
                    "first_name": "firstName",
                    "last_name": "lastName",
                    "email": "email",
                    "login": "login",
                    "middle_name": "middleName",
                    "honorific_prefix": "honorificPrefix",
                    "honorific_suffix": "honorificSuffix",
                    "title": "title",
                    "display_name": "displayName",
                    "nick_name": "nickName",
                    "profile_url": "profileUrl",
                    "second_email": "secondEmail",
                    "mobile_phone": "mobilePhone",
                    "primary_phone": "primaryPhone",
                    "street_address": "streetAddress",
                    "city": "city",
                    "state": "state",
                    "zip_code": "zipCode",
                    "country_code": "countryCode",
                    "postal_address": "postalAddress",
                    "preferred_language": "preferredLanguage",
                    "locale": "locale",
                    "timezone": "timezone",
                    "user_type": "userType",
                    "employee_number": "employeeNumber",
                    "cost_center": "costCenter",
                    "organization": "organization",
                    "division": "division",
                    "department": "department",
                    "manager_id": "managerId",
                    "manager": "manager"
                }

                set_attributes = {}

                # set only required attributes
                for item in default.keys():
                    schema_property = (getattr(schema.definitions.base.properties, item))

                    if schema_property.required:
                        set_value = input(schema_property.title + ": ")
                        set_attributes[default[item]] = set_value

                for item in schema.definitions.custom.properties.keys():
                    schema_property = (schema.definitions.custom.properties[item])

                    try:
                        if schema_property["required"]:
                            set_value = input(schema_property["title"] + ": ")
                            set_attributes[item] = set_value
                    except Exception:
                        pass

                load_optional = False

                validate_input = False

                while not validate_input:
                    input_optional = input("Populate non-required attributes? (y/n): ")

                    if input_optional.lower() == "y":
                        load_optional = True
                        validate_input = True
                    elif input_optional.lower() == "n":
                        validate_input = True

                if load_optional:
                    for item in default.keys():
                        schema_property = (getattr(schema.definitions.base.properties, item))

                        if not schema_property.required:
                            set_value = input(schema_property.title + ": ")
                            set_attributes[default[item]] = set_value

                    for item in schema.definitions.custom.properties.keys():
                        schema_property = (schema.definitions.custom.properties[item])

                        try:
                            schema_property["required"]
                        except Exception:
                            pass
                            set_value = input(schema_property["title"] + ": ")
                            set_attributes[item] = set_value

                body = {
                    'profile': set_attributes
                }

                response = await client.create_user(body)

                try:
                    print(f"Created user '{response[0].profile.login}' with ID {response[0].id}\n")
                except Exception as error:
                    print(response[2].message + "\n")

            elif line == "group":
                print("group")
            elif line == "app":
                app_name = input('Application name: ')

                print("Please select from one of the following application types")
                print('''
                                1. Web App
                                2. Single Page App
                                3. Native App (mobile)
                                4. Service App (Machine-to-Machine)
                                ''')

                menu_loop = True

                app_type = ""
                app_cred = "client_secret_post"
                app_grant = ["authorization_code"]
                app_response_type = ["code"]

                while menu_loop:

                    menu_choice = input('Enter your choice: ')

                    if menu_choice == "1":
                        app_type = "WEB"
                        menu_loop = False
                    elif menu_choice == "2":
                        app_type = "BROWSER"
                        app_cred = "none"
                        menu_loop = False
                    elif menu_choice == "3":
                        menu_loop = False
                        app_type = "NATIVE"
                    elif menu_choice == "4":
                        app_type = "SERVICE"
                        app_grant = ["client_credentials"]
                        app_response_type = ["token"]
                        menu_loop = False
                    else:
                        print("Invalid option, please select again.")

                app_redirect = ""

                if app_type != "SERVICE":
                    app_redirect = input('Enter your Redirect URI: ')

                app_body = {
                    "name": "oidc_client",
                    "label": app_name,
                    "signOnMode": "OPENID_CONNECT",
                    "credentials": {
                        "oauthClient": {
                            "token_endpoint_auth_method": app_cred
                        }
                    },
                    "settings": {
                        "oauthClient": {
                            "redirect_uris": [
                                app_redirect
                            ],
                            "response_types": app_response_type,
                            "grant_types": app_grant,
                            "application_type": app_type
                        }
                    }
                }

                app, resp, err = await client.create_application(app_body)  # .create_application(appCreate)

                if err != "None":
                    print(f"Created app '{app.label}' with client ID {app.id}\n")
                else:
                    print(err)
                    print("")

            else:
                print("Please specify what type of object you would like to create.")
                print("Valid options are 'user', 'group', or 'app'\n")

        asyncio.run(run())

    def do_exit(self, line):
        """Exit the CLI."""
        return True


def okta_login(args):
    authorizeUri = "https://" + oktaOrgUrl + "/oauth2/v1/device/authorize"

    request_body = {
        'client_id': clientId,
        'scope': 'openid okta.users.manage okta.apps.manage okta.groups.manage okta.schemas.manage'
    }

    response = requests.post(authorizeUri, data=request_body)
    response_text = json.loads(response.text)
    deviceUrl = response_text["verification_uri_complete"]
    deviceCode = response_text["device_code"]

    print(
        f'Open your browser and navigate to the following URL to begin the Okta device authorization for the Okta CLI: {deviceUrl}')

    poll = True

    while True:
        try:
            request_body = {
                'client_id': clientId,
                'device_code': deviceCode,
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            }

            response = requests.post("https://" + oktaOrgUrl + "/oauth2/v1/token", data=request_body)
            status_code = response.status_code
            if status_code != 200:
                """Continue polling"""
            else:
                response_text = json.loads(response.text)
                access_token = response_text["access_token"]
                break

        except Exception as error:
            print(error)
            raise error

    return access_token


async def main():
    parser = create_parser()
    args = parser.parse_args()

    global oktaOrgUrl
    global clientId
    global client

    if args.register and (args.login or args.clientId):
        parser.print_help()
    elif args.register:
        email = args.register
        print(email)

        first_name = input("First name: ")
        last_name = input("Last name: ")
        country = input("Country: ")

        body = {
            "userProfile": {
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "country": country,
                "okta_oie": True
            }
        }

        bodyJSON = json.dumps(body)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        reg_id = "reg405abrRAkn0TRf5d6"
        reg_url = "https://okta-devok12.okta.com/api/v1/registration/" + reg_id + "/register"
        response = requests.post(reg_url, data=bodyJSON, headers=headers)

        response_text = json.loads(response.text)

        try:
            devorg_token = response_text["developerOrgCliToken"]

            devorg_url = "https://okta-devok12.okta.com/api/internal/v1/developer/redeem/" + devorg_token
            response = requests.get(devorg_url)

            response_text = json.loads(response.text)

            try:
                status = response_text["status"]

                print("Creating new Okta Organization, this may take a minute...")
                print("An account activation email has been sent to you")
                print("Check your email to continue...")

                while status == "PENDING":
                    time.sleep(4)
                    response = requests.get(devorg_url)
                    response_text = json.loads(response.text)
                    status = response_text["status"]

                    if status != "PENDING":
                        api_token = response_text["apiToken"]
                        dev_org = response_text["orgUrl"]

                        app_grant = ["authorization_code", "urn:ietf:params:oauth:grant-type:device_code"]
                        app_response_type = ["code"]

                        app_body = {
                            "name": "oidc_client",
                            "label": "Okta CLI",
                            "signOnMode": "OPENID_CONNECT",
                            "credentials": {
                                "oauthClient": {
                                    "token_endpoint_auth_method": "none"
                                }
                            },
                            "settings": {
                                "oauthClient": {
                                    "redirect_uris": [
                                        "com.okta.developer://callback"
                                    ],
                                    "response_types": app_response_type,
                                    "grant_types": app_grant,
                                    "application_type": "NATIVE"
                                }
                            }
                        }
                        config = {
                            'authorizationMode': 'SSWS',
                            'orgUrl': dev_org,
                            'token': api_token
                        }

                        print("Creating CLI app...")
                        client = OktaClient(config)
                        app, resp, err = await client.create_application(app_body)

                        # to-do: assign Okta API scopes and assign to admin user
                        client = None

                        print(f"New Okta Account created!\nYour Okta Domain: {dev_org}\nYour CLI Client ID: {app.id}"
                              f"\nPlease relaunch the CLI and specify your org and client ID to authenticate.")

            except Exception:
                print("Failed to create Okta Organization. You can register manually by going to "
                      "https://developer.okta.com/signup")

        except Exception:
            error_causes = response_text["errorCauses"]
            print(error_causes)
            print("Failed to create Okta Organization. You can register manually by going to "
                  "https://developer.okta.com/signup")

    elif args.login and args.clientId:
        oktaOrgUrl = args.login
        clientId = args.clientId

        token = okta_login(args.login)

        config = {
            'authorizationMode': 'Bearer',
            'orgUrl': 'https://' + oktaOrgUrl,
            'token': token
        }

        client = OktaClient(config)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    if oktaOrgUrl is not None:
        OktaCLI().cmdloop()
