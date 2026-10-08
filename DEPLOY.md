# Put Eco Sphere online (free) with Streamlit Community Cloud

You need: a free **GitHub** account and a free **Streamlit Community Cloud** account (sign in with GitHub). No installer, no server.

## 1. Put the project on GitHub
1. Go to https://github.com and sign in -> **New repository** -> name it `eco-sphere` -> keep it **Public** -> **Create repository**.
2. On the new repository page click **uploading an existing file**.
3. Open this project folder on your PC and drag **all the files and folders inside it** (app.py, core.py, live.py, wizard.py, profiles.py, generate_datasets.py, train.py, requirements.txt, README.md, DEPLOY.md, the `data`, `assets` and `.streamlit` folders) into the browser window.
   * The folder called `.streamlit` starts with a dot and may be hidden. In File Explorer: View -> Show -> Hidden items.
   * If dragging folders doesn't work in your browser, use GitHub Desktop (free) or Git: `git init`, `git add .`, `git commit -m "Eco Sphere"`, `git remote add origin <your repo URL>`, `git push -u origin main`.
4. Click **Commit changes**.

## 2. Deploy
1. Go to https://share.streamlit.io and sign in with GitHub (allow access when asked).
2. Click **Create app** -> choose "Deploy a public app from GitHub".
3. Repository: `your-name/eco-sphere`, Branch: `main`, Main file path: `app.py`.
4. (Optional) Pick a custom address such as `eco-sphere-kerala` -> your link becomes `https://eco-sphere-kerala.streamlit.app`.
5. Open **Advanced settings** and choose Python **3.11** or **3.12**, then click **Deploy**.
6. Wait 3-6 minutes the first time. When the app appears, copy the link from the address bar - that is the link you share.

## 3. After it is live
* **Updating:** change a file on GitHub (pencil icon -> Commit). The app redeploys automatically.
* **Sleeping:** free apps sleep after a period of no visitors. The next visitor presses "Wake up" and waits about a minute (the models retrain on start-up).
* **Privacy:** the online app detects it is hosted and stores nothing on the server. Visitors can download/reload their own answers file.
* **Live weather** needs no key. If the forecast is unavailable the Today's Plan tab shows a message instead of made-up numbers.
* **Check the app on your phone** before sharing: open the link and complete the 5 steps.

## Other free options
* **Hugging Face Spaces** (Streamlit or Docker Space): upload the same files; the app auto-detects hosting.
* **Render / Railway**: start command `streamlit run app.py --server.port $PORT --server.address 0.0.0.0` and set the environment variable `ECO_ONLINE=1` so nothing is stored.

## Troubleshooting
* *Build fails on a package*: open **Manage app -> Logs**, copy the red error here and ask for help.
* *App says out of memory*: reboot it from **Manage app**; the app normally fits within the free limits.
* *Page keeps loading after sleeping*: wait a minute, then refresh once.
