from backend import app

# For Vercel deployment
app.debug = False

if __name__ == "__main__":
    app.run()
