# Guardians of the Gallery
A secure, dark-themed Flask image gallery that lets authenticated users upload, view, paginate, and delete images. Uploaded files are verified, stripped of metadata, normalized to PNG, and stored by content-based UUID. Missing or malformed requests are redirected to random safe sites.

## Features
- Simple username/password login with signed, time-limited cookies  
- Client-side pagination (9 thumbnails per page)  
- Secure image upload:  
  - Extension & MIME type checks  
  - Pillow verification & metadata stripping  
  - PNG normalization, optimization & content-based UUID filename  
- Bulk deletion of selected images  
- Thumbnails with checkbox overlay on hover  
- Catch-all route that redirects unknown paths to trusted sites  
- Docker-optimized multi-stage build & minimal runtime image  
- Built-in healthcheck and proper signal handling with Tini & Gunicorn  

## Prerequisites
- Docker

## Configuration
- Open .env and set your secrets and credentials:
  ```text
  SECRET_KEY=your-secret-key
  SALT=your-unique-salt
  VALID_USERNAME=admin
  VALID_PASSWORD=supersecret
  UPLOAD_FOLDER=data
  COOKIE_NAME=an2kin-guardians-of-the-gallery
  COOKIE_TIMEOUT=3600
  HOST=0.0.0.0
  PORT=3001
  FLASK_DEBUG=false
  ```

## Usage
  ```bash
  docker volume create gallery-data

  docker run -d \
    --restart always \
    --name docker-guardians-of-the-gallery \
    -p 3001:3001 \
    -v gallery-data:/app/data \
    --env-file .env \
    ghcr.io/techroy23/docker-guardians-of-the-gallery:latest
  ```


## Environment Variables
  | Variable         | Description                                            | Default                                    |
  |------------------|--------------------------------------------------------|--------------------------------------------|
  | SECRET_KEY       | Flask secret for signing cookies & sessions            | required                                   |
  | SALT             | Salt for itsdangerous token serialization              | required                                   |
  | VALID_USERNAME   | Username for login                                     | required                                   |
  | VALID_PASSWORD   | Password for login                                     | required                                   |
  | UPLOAD_FOLDER    | Directory where PNG files are stored                   | data                                       |
  | COOKIE_NAME      | Name of the authentication cookie                      | an2kin-guardians-of-the-gallery            |
  | COOKIE_TIMEOUT   | Cookie lifetime in seconds                             | 3600                                       |
  | HOST             | Host address to bind Flask/Gunicorn                    | 0.0.0.0                                    |
  | PORT             | Port to bind Flask/Gunicorn                            | 3001                                       |
  | FLASK_DEBUG      | Enable Flask debug mode (true/false)                   | false                                      |

## Project Structure
  ```text
  .
  ├── app.py
  ├── requirements.txt
  ├── Dockerfile
  ├── .env
  ├── data/                  # Uploaded images (PNG) stored here
  └── templates/
      ├── login.html
      └── main.html
  ```
