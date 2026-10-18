"""Smart Hostel Finder - synthetic dataset generator (reproducible, seed=42).
Outputs: CSVs + MySQL schema.sql + seed_data.sql"""
import random, csv, os
import pandas as pd

random.seed(42)
rng2 = random.Random(7)   # separate stream for room/facility pricing so hostel base data stays stable
OUT = os.path.dirname(os.path.abspath(__file__)) if False else "/mnt/user-data/outputs/smart_hostel_dataset"

# city: (cost multiplier, centre lat, centre lng, [(area, nearest institution)])
CITIES = {
 "Bhubaneswar": (0.90, 20.2961, 85.8245, [("Patia","KIIT University"),("Chandrasekharpur","Utkal University"),("Jaydev Vihar","Xavier University"),("Khandagiri","IIT Bhubaneswar"),("Saheed Nagar","SOA University")]),
 "Kolkata":     (1.05, 22.5726, 88.3639, [("Salt Lake","Techno India University"),("Jadavpur","Jadavpur University"),("College Street","Presidency University"),("Rajarhat","IIM Calcutta")]),
 "Bengaluru":   (1.45, 12.9716, 77.5946, [("Koramangala","Christ University"),("Electronic City","PES University"),("Yelahanka","Reva University"),("Jayanagar","Jain University")]),
 "Pune":        (1.25, 18.5204, 73.8567, [("Kothrud","MIT-WPU"),("Viman Nagar","Symbiosis International"),("Hinjewadi","Pune Institute of Computer Technology"),("Shivajinagar","Fergusson College")]),
 "Delhi":       (1.50, 28.6139, 77.2090, [("Mukherjee Nagar","Delhi University North Campus"),("Laxmi Nagar","Delhi University South Campus"),("Hauz Khas","IIT Delhi"),("Kalu Sarai","JNU")]),
 "Hyderabad":   (1.15, 17.3850, 78.4867, [("Gachibowli","IIIT Hyderabad"),("Kukatpally","JNTU Hyderabad"),("Ameerpet","Osmania University"),("Madhapur","Hyderabad Central University")]),
 "Chennai":     (1.10, 13.0827, 80.2707, [("Guindy","Anna University"),("Tharamani","IIT Madras"),("Kelambakkam","SSN College"),("Adyar","Loyola College")]),
 "Kota":        (0.80, 25.2138, 75.8648, [("Rajeev Gandhi Nagar","Coaching Hub"),("Talwandi","Coaching Hub"),("Kunhadi","Coaching Hub")]),
 "Jaipur":      (0.95, 26.9124, 75.7873, [("Malviya Nagar","MNIT Jaipur"),("Mansarovar","Manipal University Jaipur"),("Vaishali Nagar","University of Rajasthan")]),
 "Cuttack":     (0.80, 20.4625, 85.8830, [("Buxi Bazaar","Ravenshaw University"),("Link Road","SCB Medical College"),("Badambadi","NIT Rourkela Extension Centre")]),
 "Berhampur":   (0.80, 19.3149, 84.7941, [("Bhanja Bihar","Berhampur University"),("Gosaninuagaon","MKCG Medical College"),("Lanjipalli","Khallikote Autonomous College"),("Sitalapalli","Parala Maharaja Engineering College")]),
}
PREFIX = ["Sunrise","Green Valley","Scholars","Campus Nest","Urban Roost","Blue Orchid","Royal Stay","Maple","Cozy Corner","Elite","Student Haven","Lotus","Heritage","Pearl","Metro","Zenith","Orchard","Skyline","Harmony","Evergreen","Silver Oak","Golden Gate","Unity","Aspire","Neo","Bright Future","Vista","Cedar","Nirvana","Horizon"]
SUFFIX = ["Hostel","Boys Hostel","Girls Hostel","Residency","PG House","Student Living","Hall","Stay","Inn","Lodge"]
AMENITIES = ["WiFi","AC","Mess/Meals","Laundry","Gym","Parking","CCTV","Power Backup","Study Room","Hot Water","Attached Bathroom","Housekeeping","Biometric Entry","RO Drinking Water"]
# probability of each amenity per tier [budget, standard, premium]
PROB = {"WiFi":(.75,.95,1),"AC":(.05,.35,.85),"Mess/Meals":(.70,.85,.90),"Laundry":(.25,.60,.90),"Gym":(.03,.20,.60),
        "Parking":(.30,.55,.80),"CCTV":(.60,.90,1),"Power Backup":(.50,.80,.98),"Study Room":(.30,.60,.85),
        "Hot Water":(.45,.80,.97),"Attached Bathroom":(.10,.40,.85),"Housekeeping":(.35,.70,.95),
        "Biometric Entry":(.05,.30,.70),"RO Drinking Water":(.70,.90,1)}
SHARE_BASE = {1:8000, 2:5800, 3:4500, 4:3800, 5:3300}   # monthly rent per bed, Non-AC, standard tier, cost-mult 1.0
TIERS = ["budget","standard","premium"]; TIER_MULT = {"budget":0.8,"standard":1.0,"premium":1.4}

hostels, rooms, links = [], [], []
used_names = set(); hid = 0; rid = 0
for city,(cm,lat,lng,areas) in CITIES.items():
    for i in range(8):
        hid += 1
        area, inst = random.choice(areas)
        tier = random.choices(TIERS, weights=[3,4,2.5])[0]
        gender = random.choices(["Boys","Girls","Co-ed"], weights=[40,35,25])[0]
        tries = 0
        while True:
            tries += 1
            suffix = {"Boys":"Boys Hostel","Girls":"Girls Hostel"}.get(gender, random.choice(["Residency","PG House","Student Living","Hall","Stay","Inn","Lodge","Hostel"]))
            name = f"{random.choice(PREFIX)} {suffix}"
            if tries > 200: name = f"{name} {area}"  # fallback when simple names run out
            if name not in used_names: used_names.add(name); break
        food = random.choices(["Veg","Non-Veg","Both"], weights=[45,10,45])[0]
        tp = TIERS.index(tier)
        have = {a: int(random.random() < PROB[a][tp]) for a in AMENITIES}
        n_am = sum(have.values())
        dist = round(min(9, max(0.2, random.gauss({"budget":3.8,"standard":2.8,"premium":2.2}[tier], 1.6))),1)
        rating = round(min(5, max(2.6, 3.0 + 0.35*tp + 0.06*n_am - 0.05*dist + random.gauss(0,0.3))),1)
        reviews = int(max(3, random.gauss(60 + 40*tp, 35)))
        hostels.append(dict(hostel_id=hid, name=name, city=city, area=area, nearest_institution=inst,
            gender_type=gender, food_type=food, price_tier=tier, rating=rating, review_count=reviews,
            distance_to_campus_km=dist, latitude=round(lat+random.uniform(-.07,.07),5), longitude=round(lng+random.uniform(-.07,.07),5),
            contact_phone="9"+"".join(random.choices("0123456789", k=9)), established_year=random.randint(2005,2024), **have))
        for a in AMENITIES:
            if have[a]: links.append((hid, AMENITIES.index(a)+1))
        # ---- room options: sharing 1..5 x AC / Non-AC  (separate RNG stream)
        tmult = TIER_MULT[tier]
        for sh in sorted(rng2.sample([1,2,3,4,5], k=rng2.choice([3,4,4,5]))):
            for ac in (0,1):
                if ac and not (have["AC"] and (sh <= 2 or rng2.random() < .6)): continue
                bath = have["Attached Bathroom"] and sh <= 3
                rent = SHARE_BASE[sh]*cm*tmult*(1.25 if ac else 1)*(1.1 if bath else 1)*rng2.uniform(.92,1.08)
                rent = int(round(rent/100)*100)
                rid += 1
                total = rng2.choice([4,6,8,10,12,20])
                rooms.append(dict(option_id=rid, hostel_id=hid, sharing_capacity=sh, ac_type="AC" if ac else "Non-AC",
                    attached_bathroom=int(bath), monthly_rent=rent, security_deposit=rent*rng2.choice([1,1,2]),
                    total_rooms=total, rooms_available=rng2.randint(0,total)))
        # ---- facility prices (INR / month; 0 = not offered)
        hostels[-1]["mess_price"] = int(round(2500*cm*{"budget":.9,"standard":1,"premium":1.25}[tier]*rng2.uniform(.9,1.1)/100)*100) if have["Mess/Meals"] else 0
        hostels[-1]["laundry_price"] = int(round(rng2.uniform(300,600)*cm*{"budget":.9,"standard":1,"premium":1.3}[tier]/50)*50) if have["Laundry"] else 0
        hostels[-1]["gym_price"] = int(round(rng2.uniform(400,900)*cm/50)*50) if have["Gym"] else 0
        hostels[-1]["parking_price"] = int(round(rng2.uniform(200,500)*cm/50)*50) if have["Parking"] else 0

H = pd.DataFrame(hostels); R = pd.DataFrame(rooms)
REMOVED = ["Gym","Parking"]                       # sections removed per request
AMENITIES_OUT = [a for a in AMENITIES if a not in REMOVED]
H = H.drop(columns=["gym_price","parking_price"]+REMOVED)
links = [(h, AMENITIES_OUT.index(AMENITIES[a-1])+1) for h,a in links if AMENITIES[a-1] not in REMOVED]
agg = R.groupby("hostel_id").agg(min_rent=("monthly_rent","min"), max_rent=("monthly_rent","max"), avg_rent=("monthly_rent","mean")).round(0).astype(int)
for sh in range(1,6): agg[f"has_{sh}_sharing"] = R[R.sharing_capacity==sh].groupby("hostel_id").size().reindex(agg.index).fillna(0).gt(0).astype(int)
agg["has_non_ac_rooms"] = R[R.ac_type=="Non-AC"].groupby("hostel_id").size().reindex(agg.index).fillna(0).gt(0).astype(int)
agg["has_ac_rooms"] = R[R.ac_type=="AC"].groupby("hostel_id").size().reindex(agg.index).fillna(0).gt(0).astype(int)
H = H.merge(agg, on="hostel_id")
H["has_both_ac_and_non_ac"] = (H.has_ac_rooms & H.has_non_ac_rooms).astype(int)
H["amenity_count"] = H[AMENITIES_OUT].sum(axis=1)
colmap = {a: a.lower().replace("/","_").replace(" ","_") for a in AMENITIES_OUT}
H.rename(columns=colmap).to_csv(f"{OUT}/hostels_feature_matrix.csv", index=False)
R.to_csv(f"{OUT}/room_options.csv", index=False)
pd.DataFrame({"amenity_id":range(1,len(AMENITIES_OUT)+1),"amenity_name":AMENITIES_OUT}).to_csv(f"{OUT}/amenities.csv", index=False)
pd.DataFrame(links, columns=["hostel_id","amenity_id"]).to_csv(f"{OUT}/hostel_amenities.csv", index=False)

# ---- human-readable pricing sheet: one row per hostel
def fmt(df):
    return " | ".join(f"{int(r.sharing_capacity)} Sharing - Rs {int(r.monthly_rent):,}" for r in df.sort_values("sharing_capacity").itertuples())
rows = []
for h in H.itertuples():
    ro = R[R.hostel_id == h.hostel_id]
    ac = ro[ro.ac_type == "AC"]; nac = ro[ro.ac_type == "Non-AC"]
    rows.append({
        "hostel_id": h.hostel_id, "hostel_name": h.name, "city": h.city, "area": h.area, "gender_type": h.gender_type,
        "ac_available": "Yes" if len(ac) else "No",
        "ac_and_non_ac_both_available": "Yes" if (len(ac) and len(nac)) else "No",
        "room_category": "Both AC and Non-AC" if (len(ac) and len(nac)) else ("AC only" if len(ac) else "Non-AC only"),
        "ac_room_types_and_price": fmt(ac) if len(ac) else "Not available",
        "non_ac_room_types_and_price": fmt(nac),
        "mess_available": "Yes" if h.mess_price else "No",
        "mess_price_per_month": h.mess_price if h.mess_price else "Not available",
        "laundry_available": "Yes" if h.laundry_price else "No",
        "laundry_price_per_month": h.laundry_price if h.laundry_price else "Not available"})
pd.DataFrame(rows).to_csv(f"{OUT}/hostel_pricing_sheet.csv", index=False)

# ---- sample user preference profiles for testing the recommender
prefs = [
 (1,"Bhubaneswar","Boys",6000,2,"Non-AC","WiFi;Mess/Meals;Hot Water",3,"Veg",.35,.20,.30,.15),
 (2,"Bengaluru","Girls",14000,1,"AC","WiFi;CCTV;Attached Bathroom",4,"Any",.20,.15,.35,.30),
 (3,"Kota","Boys",5000,3,"Non-AC","Study Room;Mess/Meals;Power Backup",2,"Veg",.40,.25,.20,.15),
 (4,"Delhi","Girls",10000,2,"Any","CCTV;Biometric Entry;WiFi",5,"Any",.25,.25,.25,.25),
 (5,"Pune","Co-ed",8000,3,"Non-AC","WiFi;Laundry;Study Room",3,"Both",.30,.15,.35,.20),
 (6,"Hyderabad","Boys",9000,2,"AC","WiFi;Power Backup",4,"Non-Veg",.30,.20,.30,.20),
 (7,"Chennai","Girls",9000,1,"Any","WiFi;Hot Water;Housekeeping",3,"Veg",.25,.25,.25,.25),
 (8,"Kolkata","Boys",5000,4,"Non-AC","Mess/Meals;RO Drinking Water",5,"Any",.50,.20,.15,.15),
 (9,"Jaipur","Co-ed",6500,2,"Non-AC","WiFi;Study Room;CCTV",3,"Veg",.30,.20,.30,.20),
 (10,"Cuttack","Girls",5000,3,"Non-AC","CCTV;Hot Water;WiFi",4,"Veg",.40,.20,.25,.15),
 (11,"Berhampur","Boys",5000,2,"Non-AC","WiFi;Mess/Meals;Power Backup",3,"Veg",.35,.20,.30,.15),
 (12,"Berhampur","Girls",6500,3,"Any","CCTV;WiFi;Hot Water",4,"Any",.30,.25,.25,.20)]
pd.DataFrame(prefs, columns=["user_id","city","gender","max_budget","sharing_capacity","ac_preference","must_have_amenities","max_distance_km","food_pref","w_price","w_distance","w_amenities","w_rating"]).to_csv(f"{OUT}/sample_user_preferences.csv", index=False)

# ---- MySQL
SCHEMA = """-- Smart Hostel Finder - MySQL schema
CREATE DATABASE IF NOT EXISTS smart_hostel_finder CHARACTER SET utf8mb4;
USE smart_hostel_finder;
DROP TABLE IF EXISTS hostel_amenities; DROP TABLE IF EXISTS room_options; DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS amenities; DROP TABLE IF EXISTS hostels;

CREATE TABLE hostels (
  hostel_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  city VARCHAR(50) NOT NULL,
  area VARCHAR(80) NOT NULL,
  nearest_institution VARCHAR(120),
  gender_type ENUM('Boys','Girls','Co-ed') NOT NULL,
  food_type ENUM('Veg','Non-Veg','Both') NOT NULL,
  price_tier ENUM('budget','standard','premium') NOT NULL,
  rating DECIMAL(2,1) NOT NULL CHECK (rating BETWEEN 0 AND 5),
  review_count INT NOT NULL DEFAULT 0,
  distance_to_campus_km DECIMAL(3,1) NOT NULL CHECK (distance_to_campus_km >= 0),
  latitude DECIMAL(8,5), longitude DECIMAL(8,5),
  contact_phone CHAR(10),
  established_year SMALLINT,
  mess_price INT NOT NULL DEFAULT 0 COMMENT 'INR/month, 0 = not offered',
  laundry_price INT NOT NULL DEFAULT 0 COMMENT 'INR/month, 0 = not offered',
  INDEX idx_city (city), INDEX idx_gender (gender_type), INDEX idx_rating (rating)
);
CREATE TABLE room_options (
  option_id INT PRIMARY KEY AUTO_INCREMENT,
  hostel_id INT NOT NULL,
  sharing_capacity TINYINT NOT NULL CHECK (sharing_capacity BETWEEN 1 AND 5),
  ac_type ENUM('AC','Non-AC') NOT NULL,
  attached_bathroom TINYINT(1) NOT NULL DEFAULT 0,
  monthly_rent INT NOT NULL CHECK (monthly_rent > 0) COMMENT 'INR per bed per month, excludes mess/laundry',
  security_deposit INT NOT NULL DEFAULT 0,
  total_rooms INT NOT NULL,
  rooms_available INT NOT NULL,
  FOREIGN KEY (hostel_id) REFERENCES hostels(hostel_id) ON DELETE CASCADE,
  UNIQUE KEY uq_option (hostel_id, sharing_capacity, ac_type),
  INDEX idx_rent (monthly_rent), INDEX idx_sharing (sharing_capacity)
);
CREATE TABLE amenities (
  amenity_id INT PRIMARY KEY AUTO_INCREMENT,
  amenity_name VARCHAR(50) NOT NULL UNIQUE
);
CREATE TABLE hostel_amenities (
  hostel_id INT NOT NULL, amenity_id INT NOT NULL,
  PRIMARY KEY (hostel_id, amenity_id),
  FOREIGN KEY (hostel_id) REFERENCES hostels(hostel_id) ON DELETE CASCADE,
  FOREIGN KEY (amenity_id) REFERENCES amenities(amenity_id) ON DELETE CASCADE
);
"""
open(f"{OUT}/schema.sql","w").write(SCHEMA)
q = lambda v: "NULL" if v is None else (f"'{str(v).replace(chr(39), chr(39)*2)}'" if isinstance(v,str) else str(v))
def ins(table, cols, rows):
    out=[]
    for i in range(0,len(rows),50):
        out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n" + ",\n".join("("+", ".join(q(v) for v in r)+")" for r in rows[i:i+50])+";")
    return "\n".join(out)
hc = ["hostel_id","name","city","area","nearest_institution","gender_type","food_type","price_tier","rating","review_count","distance_to_campus_km","latitude","longitude","contact_phone","established_year","mess_price","laundry_price"]
rc = list(R.columns)
sql = "USE smart_hostel_finder;\n" + ins("amenities",["amenity_id","amenity_name"],[(i+1,a) for i,a in enumerate(AMENITIES_OUT)]) + "\n\n" \
  + ins("hostels",hc,[tuple(r) for r in H[hc].itertuples(index=False)]) + "\n\n" \
  + ins("room_options",rc,[tuple(x if isinstance(x,str) else int(x) for x in r) for r in R[rc].itertuples(index=False)]) + "\n\n" \
  + ins("hostel_amenities",["hostel_id","amenity_id"],links) + "\n"
open(f"{OUT}/seed_data.sql","w").write(sql)
print(len(H),"hostels",len(R),"room options",len(links),"links")
