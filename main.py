import cmd
import argparse
import requests
import json
import asyncio
import os

import okta.models as models
from okta.client import Client as OktaClient

loop = asyncio.get_event_loop()

oktaOrgUrl = ""
clientId = ""
client = OktaClient()


def create_parser():
    parser = argparse.ArgumentParser(description="Okta Command Line Interface")

    parser.add_argument('-l', '--login', metavar="", help='Log into your Okta org', required=True)
    parser.add_argument('-c', '--clientId', metavar="", help="OIDC client ID for CLI app", required=True)

    return parser


class OktaCLI(cmd.Cmd):
    prompt = '>>'
    intro = 'Welcome to the Okta CLI. Type \'help\' for available commands'

    def do_list(self, line):
        """List objects in your org; valid options are users, groups, or apps"""

        async def run():
            if line == "users":
                users, resp, error = await client.list_users()

                for user in users:
                    print(user.profile.first_name, user.profile.last_name)
            elif line == "apps":
                print("apps")
            elif line == "groups":
                print("groups")
            else:
                print("Please specify what objects you would like to create.")
                print("Valid options are 'users', 'groups', or 'apps'")

        asyncio.run(run())

    def do_create(self, line):
        """Create objects in your org; valid options are user, group, or app"""

        async def run():
            if line == "user":
                schema, resp, error = await client.get_user_schema("default")

                # default attributes
                default_properties = [
                    "first_name",
                    "last_name",
                    "email",
                    "login",
                    "middle_name",
                    "honorific_prefix",
                    "honorific_suffix",
                    "title",
                    "display_name",
                    "nick_name",
                    "profile_url",
                    "second_email",
                    "mobile_phone",
                    "primary_phone",
                    "street_address",
                    "city",
                    "state",
                    "zip_code",
                    "country_code",
                    "postal_address",
                    "preferred_language",
                    "locale",
                    "timezone",
                    "user_type",
                    "employee_number",
                    "cost_center",
                    "organization",
                    "division",
                    "department",
                    "manager_id",
                    "manager"
                ]

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
                for item in default_properties:
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
                    for item in default_properties:
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
                    print(f"Created user '{response[0].profile.login}' with ID {response[0].id}")
                except Exception as error:
                    print(response[2].message)

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
                    print(f"Created app '{app.label}' with client ID {app.id}")
                else:
                    print(err)

            else:
                print("Please specify what type of object you would like to create.")
                print("Valid options are 'user', 'group', or 'app'")

        asyncio.run(run())

    def do_exit(self, line):
        """Exit the CLI."""
        return True


def okta_login(args):
    authorizeUri = "https://" + oktaOrgUrl + "/oauth2/v1/device/authorize"

    requestBody = {
        'client_id': clientId,
        'scope': 'openid okta.users.manage okta.apps.manage okta.groups.manage okta.schemas.manage'
    }

    response = requests.post(authorizeUri, data=requestBody)
    responseText = json.loads(response.text)
    deviceUrl = responseText["verification_uri_complete"]
    deviceCode = responseText["device_code"]

    print(
        f'Open your browser and navigate to the following URL to begin the Okta device authorization for the Okta CLI: {deviceUrl}')

    poll = True

    while True:
        try:
            requestBody = {
                'client_id': clientId,
                'device_code': deviceCode,
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            }

            response = requests.post("https://" + oktaOrgUrl + "/oauth2/v1/token", data=requestBody)
            statusCode = response.status_code
            if statusCode != 200:
                """Continue polling"""
            else:
                responseText = json.loads(response.text)
                accessToken = responseText["access_token"]
                break

        except Exception as error:
            print(error)
            raise error

    return accessToken


async def main():
    parser = create_parser()
    args = parser.parse_args()

    global oktaOrgUrl
    global clientId
    global client

    oktaOrgUrl = args.login
    clientId = args.clientId

    if args.login:
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
    OktaCLI().cmdloop()
