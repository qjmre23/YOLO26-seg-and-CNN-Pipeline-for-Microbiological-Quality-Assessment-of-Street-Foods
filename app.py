import os
from datetime import datetime
from flask import Flask, render_template_string, request

import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>E-Sawsaw S3 Test</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; }
        .success { color: green; background: #eaffea; padding: 15px; border-radius: 5px; }
        .error   { color: red;   background: #ffeaea; padding: 15px; border-radius: 5px; }
        input[type=text] { width: 100%; padding: 8px; margin: 8px 0; box-sizing: border-box; }
        button { background: #0066cc; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        pre { background: #f4f4f4; padding: 10px; border-radius: 5px; word-wrap: break-word; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h1>E-Sawsaw — S3 Connectivity Test</h1>
    <form method="POST">
        <label>Test message to upload:</label>
        <input type="text" name="message" value="Hello from E-Sawsaw on Render!" required>
        <br><br>
        <button type="submit">Upload to S3</button>
    </form>

    {% if result %}
        <br>
        <div class="{{ result.status }}">
            <strong>{{ result.heading }}</strong>
            <pre>{{ result.body }}</pre>
        </div>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    result = None

    if request.method == "POST":
        message = request.form.get("message", "")
        try:
            bucket = os.environ["S3_BUCKET_NAME"]
            s3 = boto3.client("s3")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            key = f"test/render_test_{timestamp}.txt"
            content = (
                f"E-Sawsaw S3 test from Render\n"
                f"Timestamp : {timestamp}\n"
                f"Message   : {message}\n"
                f"Bucket    : {bucket}\n"
                f"Region    : {os.environ.get('AWS_DEFAULT_REGION', 'not set')}\n"
            )

            # Upload
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="text/plain"
            )

            # Presigned URL
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=300
            )

            result = {
                "status": "success",
                "heading": "SUCCESS — File uploaded to S3",
                "body": (
                    f"S3 Key     : {key}\n"
                    f"Bucket     : {bucket}\n\n"
                    f"Presigned URL (valid 5 min):\n{url}"
                )
            }

        except KeyError as e:
            result = {
                "status": "error",
                "heading": "FAILED — Missing environment variable",
                "body": f"{e}\n\nMake sure you added all secrets in Render → Environment."
            }
        except ClientError as e:
            result = {
                "status": "error",
                "heading": "FAILED — AWS Error",
                "body": str(e)
            }
        except Exception as e:
            result = {
                "status": "error",
                "heading": "FAILED — Unexpected error",
                "body": str(e)
            }

    return render_template_string(HTML, result=result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
