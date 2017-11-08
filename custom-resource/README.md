## Approval for Cloudformation stack launch using Lambda as custom resource
Let’s say you need to build an approval workflow for stack launch. AWS CloudFormation features like WaitCondition and WaitHandle, along with AWS Lambda as a custom resource we can create a simple approval workflow. This template would build required AWS Lambda, Amazon API Gateway, Amazon SNS to do the setup.

You can use Lambda ARN from the output to configure custom resource. To know more you can refer to this [blog](https://aws.amazon.com/blogs/apn/how-to-create-an-approval-flow-for-an-aws-service-catalog-product-launch-using-aws-lambda/)
