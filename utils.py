import json


def archive_floors(sub_name):
    floors_archived = {}
    floors_unarchived = {}
    with open(f"data/{sub_name}/floors.json", encoding="utf-8") as f:
        all_floors = json.loads(f.read())
    for post_id, post in all_floors.items():
        floors = post["floors"]

        floors_archived[post_id] = {}
        floors_archived[post_id]["meta"] = {}
        floors_archived[post_id]["floors"] = {}

        floors_unarchived[post_id] = {}
        floors_unarchived[post_id]["meta"] = {}
        floors_unarchived[post_id]["floors"] = {}

        for floor_num, floor in floors.items():
            if floor["replied"]:
                floors_archived[post_id]["meta"] = post["meta"]
                floors_archived[post_id]["floors"][floor_num] = floor
            else:
                floors_unarchived[post_id]["meta"] = post["meta"]
                floors_unarchived[post_id]["floors"][floor_num] = floor
    floors_archived = {
        post_id: post
        for post_id, post in floors_archived.items()
        if post and post["floors"]
    }
    floors_unarchived = {
        post_id: post
        for post_id, post in floors_unarchived.items()
        if post and post["floors"]
    }
    with open(f"data/{sub_name}/floors_archived.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(floors_archived, indent=4, ensure_ascii=False))
    with open(f"data/{sub_name}/floors.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(floors_unarchived, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    archive_floors("lol")
