-- Smart Hostel Finder - MySQL schema
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
