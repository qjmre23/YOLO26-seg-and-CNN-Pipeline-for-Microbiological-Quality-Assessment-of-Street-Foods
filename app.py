import os
from datetime import datetime
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask import Flask, render_template_string, request

app = Flask(__name__)

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

        h1 {
            margin-bottom: 10px;
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
    <p>Railway → Flask → AWS S3 image storage test</p>

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

                    <h2>Upload Successful</h2>

                    <pre>{{ result.message }}</pre>

                    <p>
                        <strong>Stored image:</strong>
                    </p>

                    <img src="{{ result.url }}" alt="Uploaded image">

                    <p>
                        <a href="{{ result.url }}" target="_blank">
                            Open temporary S3 URL
                        </a>
                    </p>

                </div>

            {% else %}

                <div class="error">

                    <h2>Upload Failed</h2>

                    <pre>{{ result.message }}</pre>

                </div>

            {% endif %}

        </div>

    {% endif %}

</body>
</html>
"""


app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


@app.route("/", methods=["GET", "POST"])
def home():

    result = None

    if request.method == "POST":

        image_file = request.files.get("plate_image")

        if not image_file or image_file.filename == "":
            result = {
                "success": False,
                "message": "No image was selected."
            }

            return render_template_string(HTML, result=result)

        # Only allow JPG and PNG for this test
        allowed_types = {
            "image/jpeg": ".jpg",
            "image/png": ".png"
        }

        if image_file.content_type not in allowed_types:
            result = {
                "success": False,
                "message": (
                    "Invalid image type.\n"
                    "Please upload a JPG or PNG image."
                )
            }

            return render_template_string(HTML, result=result)

        try:

            # Read image directly into memory.
            # Nothing is written to Railway's disk.
            image_bytes = image_file.read()

            if not image_bytes:
                raise ValueError("The uploaded image is empty.")

            bucket = os.environ["S3_BUCKET_NAME"]
            region = os.environ.get(
                "AWS_DEFAULT_REGION",
                "ap-southeast-1"
            )

            s3 = boto3.client(
                "s3",
                region_name=region
            )

            # Generate a unique sample ID.
            timestamp = datetime.utcnow().strftime(
                "%Y%m%d_%H%M%S"
            )

            sample_id = (
                f"sample_{timestamp}_{uuid4().hex[:8]}"
            )

            extension = allowed_types[image_file.content_type]

            # E-Sawsaw's planned S3 structure
            key = f"raw/{sample_id}{extension}"

            # Upload directly from RAM to S3
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=image_bytes,
                ContentType=image_file.content_type
            )

            # Generate temporary URL.
            # The S3 object remains private.
            url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key
                },
                ExpiresIn=300
            )

            result = {
                "success": True,
                "message": (
                    f"Sample ID : {sample_id}\n"
                    f"S3 Bucket : {bucket}\n"
                    f"S3 Key    : {key}\n"
                    f"Size      : {len(image_bytes):,} bytes\n"
                    f"Type      : {image_file.content_type}\n"
                    f"Region    : {region}\n\n"
                    "The image was uploaded directly from "
                    "Railway memory to S3."
                ),
                "url": url
            }

        except KeyError as e:

            result = {
                "success": False,
                "message": (
                    f"Missing Railway environment variable: {e}\n\n"
                    "Check Railway → Variables."
                )
            }

        except NoCredentialsError:

            result = {
                "success": False,
                "message": (
                    "AWS credentials were not found.\n\n"
                    "Check these Railway variables:\n"
                    "AWS_ACCESS_KEY_ID\n"
                    "AWS_SECRET_ACCESS_KEY\n"
                    "AWS_DEFAULT_REGION\n"
                    "S3_BUCKET_NAME"
                )
            }

        except ClientError as e:

            result = {
                "success": False,
                "message": (
                    "AWS/S3 error:\n\n"
                    f"{e}"
                )
            }

        except Exception as e:

            result = {
                "success": False,
                "message": (
                    "Unexpected error:\n\n"
                    f"{type(e).__name__}: {e}"
                )
            }

    return render_template_string(
        HTML,
        result=result
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
