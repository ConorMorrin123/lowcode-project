from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>Hello from Conor Morrin</h1>"

@app.route("/about")
def about():
    return """<p>If I had a full evening to work on this app I would add give more details about myself. I would make it more of a profile like page. Multible tabs to include images, interests plans for the future. Combine social media apps like LinkedIn and Instagram to make an overall profile for myself rather than sperate lifestyles. <br> First: I would create main profile page. It would include my name, age, job occupation and the general location of where I am from and live. It would also include a profile picture image. <br> Second: I love music so I would add a page about my current playlists. I would include a playlist of my favorite songs of the month. My recommended albums to listen to etc.</p>"""

if __name__ == "__main__":
    app.run(debug=True)
