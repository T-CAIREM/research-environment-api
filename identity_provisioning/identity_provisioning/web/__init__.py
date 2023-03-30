from flask import Flask

app = Flask(__name__)

# NOTE: This initializes the logger.
# Without a reference, the formatters are not applied.
app.logger
