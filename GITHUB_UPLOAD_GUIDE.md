# GitHub upload instructions — AttendIQ first draft (Neon edition)

1. Download and extract `AttendIQ_First_Draft_Neon.zip`.
2. Open https://github.com/Davidnna/AttendIQ in your browser.
3. Select **Add file → Upload files**.
4. Upload the extracted project contents so that `manage.py`, `render.yaml`, `requirements.txt`, and the folders `config`, `core`, `accounts`, `templates`, and `static` appear at the repository root.
5. Do not upload the ZIP file itself as the only repository file.
6. Commit directly to `main` with this exact message:

   `Create AttendIQ branded Django foundation with Neon PostgreSQL`

7. Create the Neon PostgreSQL project in Frankfurt and copy both pooled and direct connection strings. Keep them private.
8. In Render, choose **New → Blueprint**, connect `Davidnna/AttendIQ`, and provide the two connection strings when prompted:
   - `DATABASE_URL`: pooled Neon connection string (host contains `-pooler`)
   - `DIRECT_DATABASE_URL`: direct Neon connection string (host does not contain `-pooler`)

Do not create or upload a `.env` file. The `.env.example` file contains placeholders only.
