python3 -m venv myenv
source myenv/bin/activate

cp .env.local.example .env.local

pip install fastapi uvicorn requests pydantic bson
pip install PyJWT bcrypt pymongo python-multipart

python3 create_user.py user1 password1
python3 create_user.py user2 password2

python3 create_user.py alice alicepassword
python3 create_user.py bob bobpassword


mongod --auth --bind_ip 127.0.0.1 --dbpath "$(brew --prefix)/var/mongodb" --logpath "$(brew --prefix)/var/log/mongodb/mongo.log" --logappend

uvicorn server:app --reload --port 9001


python3 client.py \
  --base-url http://localhost:9001 \
  --username user1 \
  --password password1 \
  --recipient-user-id <recipient_user_id> \
  --file ~/dev/c545_proj/test.webm \
  --content-type application/octet-stream


--install mongodb driver for python projects
pip install pymongo


--install mongodb
brew tap mongodb/brew
brew install mongodb-community

--run mongodb
brew services start mongodb/brew/mongodb-community
--if needed run at elevated permissions
sudo brew services start mongodb/brew/mongodb-community

--verify
mongosh

MongoDB will run on localhost:27017


mongod --auth --bind_ip 127.0.0.1 --dbpath "$(brew --prefix)/var/mongodb" --logpath "$(brew --prefix)/var/log/mongodb/mongo.log" --logappend


--password: password
mongosh -u admin -p --authenticationDatabase admin

use app_data
db.users.find().pretty()

use app_data
db.fs.files.find().pretty()

--Swagger documentation
http://localhost:9001/docs