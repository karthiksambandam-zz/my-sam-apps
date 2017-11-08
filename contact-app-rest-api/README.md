## Address Book Rest API
This template helps in creating rest api for managing simple contact info for an address book app. The idea is to emphasis APIGateway features like AWS integration, Stage Variables, request transformation etc. Basically, this will create API GW as proxy to DynamoDB. This is also to showcase that API GW can be used to directly integrate with AWS services.

#### To test
To test the api created use the API gateway console. From the resources section you would be able to test.

Sample JSON for /contact/{id} Post method:
```
{
  "id":{"S":"1001"},
  "fullname":{"S":"first last"},
  "phone":{"S":"123-456-7890"}
}
```
