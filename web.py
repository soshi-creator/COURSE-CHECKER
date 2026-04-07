from pymongo import MongoClient

client = MongoClient("mongodb+srv://David:David@cluster0.nb9xn9p.mongodb.net/?appName=Cluster0")
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