import os
from datetime import datetime
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask import Flask, render_template_string, request

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>E-Sawsaw - Railway S3 Test</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 700px;
            margin: 40px auto;
            padding: 20px;
        }

        .box {
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 10px;
            margin-top: 20px;
        }

        .success {
            background: #eaffea;
            border: 1px solid #65b765;
            padding: 15px;
            border-radius: 8px;
        }

        .error {
            background: #ffeaea;
            border: 1px solid #d9534f;
            padding: 15px;
            border-radius: 8px;
        }

        input[type=file] {
            margin: 15px 0;
        }

        button {
            background: #0066cc;
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 15px;
        }

        button:hover {
            background: #0052a3;
        }

        img {
            max-width: 100%;
            margin-top: 15px;
            border-radius: 8px;
        }

        pre {
            white-space: pre-wrap;
            word-break: break-word;
            background: #f5f5f5;
            padding: 12px;
            border-radius: 6px;
        }
    </style>
</head>

<body>

    <h1>E-Sawsaw</h1>

    <p>
        Railway → Flask → AWS S3 image storage test
    </p>

    <div class="box">

        <form method="POST" enctype="multipart/form-data">

            <label>
                <strong>Select a plate image:</strong>
            </label>

            <br>

            <input
                type="file"
                name="plate_image"
                accept="image/jpeg,image/png"
                required
            >

            <br>

            <button type="submit">
                Upload Image to S3
            </button>

        </form>

    </div>

    {% if result %}

        <div class="box">

            {% if result.success %}

                <div class="success">

                    <h2>✅ Upload Successful</h2>

                    <pre>{{ result.message }}</pre>

                    <h3>Stored Image</h3>

                    <img
                        src="{{ result.url }}"
                        alt="Uploaded image"
                    >

                    <p>
                        <a
                            href="{{ result.url }}"
                            target="_blank"
                        >
                            Open temporary S3 URL
                        </a>
                    </p>

                </div>

            {% else %}

                <div class="error">

                    <h2>❌ Upload Failed</h2>

                    <pre>{{ result.message }}</pre>

                </div>

            {% endif %}

        </div>

    {% endif %}

</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def home():

    result = None

    if request.method == "POST":

        image_file = request.files.get("plate_image")

        if not image_file or not image_file.filename:

            result = {
                "success": False,
                "message": "No image was selected."
            }

            return render_template_string(
                HTML,
                result=result
            )

        allowed_types = {
            "image/jpeg": ".jpg",
            "image/png": ".png"
        }

        if image_file.content_type not in allowed_types:

            result = {
                "success": False,
                "message": (
                    "Only JPG and PNG images are allowed."
                )
            }

            return render_template_string(
                HTML,
                result=result
            )

        try:

            # ==========================================
            # READ RAILWAY ENVIRONMENT VARIABLES
            # ==========================================

            access_key = os.environ.get(
                "AWS_ACCESS_KEY_ID"
            )

            secret_key = os.environ.get(
                "AWS_SECRET_ACCESS_KEY"
            )

            region = os.environ.get(
                "AWS_DEFAULT_REGION"
            )

            bucket = os.environ.get(
                "S3_BUCKET_NAME"
            )

            # Check which variables are missing.
            missing = []

            if not access_key:
                missing.append("AWS_ACCESS_KEY_ID")

            if not secret_key:
                missing.append("AWS_SECRET_ACCESS_KEY")

            if not region:
                missing.append("AWS_DEFAULT_REGION")

            if not bucket:
                missing.append("S3_BUCKET_NAME")

            if missing:

                raise RuntimeError(
                    "Missing Railway environment variables:\n\n"
                    + "\n".join(
                        f"❌ {variable}"
                        for variable in missing
                    )
                    + "\n\n"
                    "Check Railway → your service → Variables."
                )

            # ==========================================
            # DEBUG CHECK
            # Does NOT print secret values.
            # ==========================================

            print("========== AWS ENV CHECK ==========")
            print(
                "AWS_ACCESS_KEY_ID:",
                bool(access_key)
            )
            print(
                "AWS_SECRET_ACCESS_KEY:",
                bool(secret_key)
            )
            print(
                "AWS_DEFAULT_REGION:",
                region
            )
            print(
                "S3_BUCKET_NAME:",
                bucket
            )
            print("====================================")

            # ==========================================
            # READ IMAGE INTO MEMORY
            # ==========================================

            image_bytes = image_file.read()

            if not image_bytes:

                raise RuntimeError(
                    "The uploaded image is empty."
                )

            # ==========================================
            # CREATE S3 CLIENT
            # EXPLICITLY PASS AWS CREDENTIALS
            # ==========================================

            s3 = boto3.client(
                "s3",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )

            # ==========================================
            # CREATE UNIQUE SAMPLE ID
            # ==========================================

            timestamp = datetime.utcnow().strftime(
                "%Y%m%d_%H%M%S"
            )

            sample_id = (
                f"sample_{timestamp}_"
                f"{uuid4().hex[:8]}"
            )

            extension = allowed_types[
                image_file.content_type
            ]

            # E-Sawsaw S3 structure
            key = f"raw/{sample_id}{extension}"

            # ==========================================
            # UPLOAD IMAGE TO S3
            # ==========================================

            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=image_bytes,
                ContentType=image_file.content_type
            )

            # ==========================================
            # GENERATE TEMPORARY PRIVATE URL
            # ==========================================

            url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key
                },
                ExpiresIn=300
            )

            # ==========================================
            # SUCCESS
            # ==========================================

            result = {
                "success": True,

                "message": (
                    f"Sample ID : {sample_id}\n"
                    f"S3 Bucket : {bucket}\n"
                    f"S3 Key    : {key}\n"
                    f"File Size : "
                    f"{len(image_bytes):,} bytes\n"
                    f"File Type : "
                    f"{image_file.content_type}\n"
                    f"Region    : {region}\n\n"
                    "SUCCESS!\n"
                    "The image was uploaded directly "
                    "from Railway memory to S3."
                ),

                "url": url
            }

        except RuntimeError as e:

            result = {
                "success": False,
                "message": str(e)
            }

        except NoCredentialsError:

            result = {
                "success": False,
                "message": (
                    "Boto3 still cannot authenticate "
                    "with AWS.\n\n"
                    "The Railway variables were either "
                    "not passed correctly or the AWS "
                    "credentials are invalid."
                )
            }

        except ClientError as e:

            result = {
                "success": False,
                "message": (
                    "AWS/S3 ERROR:\n\n"
                    f"{e}"
                )
            }

        except Exception as e:

            result = {
                "success": False,
                "message": (
                    f"{type(e).__name__}:\n\n"
                    f"{e}"
                )
            }

    return render_template_string(
        HTML,
        result=result
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get("PORT", 10000)
        )
    )
