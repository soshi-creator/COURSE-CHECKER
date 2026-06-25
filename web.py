from pymongo import MongoClient
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient("MONGO_URI")
db = client["course_checker"]
courses = db["courses"]

# Geography → History (16 → 14)
courses.update_many(
    {"cluster": 16},
    {"$set": {"cluster": 14}}
)

# Religion → Cluster 18 (20 → 18)
courses.update_many(
    {"cluster": 20},
    {"$set": {"cluster": 18}}
)

# Education → Cluster 17 (19 → 17)
courses.update_many(
    {"cluster": 19},
    {"$set": {"cluster": 17}}
)

print("Cluster merges completed ✅")
