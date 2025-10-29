
CREATE TABLE universities (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name          VARCHAR(200) NOT NULL,
  UNIQUE KEY uq_university_name (name)
) ENGINE=InnoDB;


CREATE TABLE users (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name            VARCHAR(120) NOT NULL,
  username        VARCHAR(60)  NOT NULL,
  email           VARCHAR(254) NOT NULL,
  password_hash   VARBINARY(100) NOT NULL,   
  photo_url       VARCHAR(500),              
  latitude        DECIMAL(9,6),              
  longitude       DECIMAL(9,6),
  role            ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
  university_id   BIGINT UNSIGNED,


  CONSTRAINT fk_users_university
    FOREIGN KEY (university_id) REFERENCES universities(id)
      ON UPDATE CASCADE ON DELETE SET NULL,

  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;


CREATE TABLE event_types (
  id   BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(40) NOT NULL,           
  UNIQUE KEY uq_event_type_code (code)
) ENGINE=InnoDB;


CREATE TABLE events (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  owner_user_id   BIGINT UNSIGNED NOT NULL,  
  title           VARCHAR(200) NOT NULL,
  explanation     TEXT NOT NULL,
  type_id         BIGINT UNSIGNED,               
  price           DECIMAL(10,2) NOT NULL,
  starts_at       DATETIME NOT NULL,
  ends_at         DATETIME,
  location_name   VARCHAR(500),
  photo_url       VARCHAR(500),
  status          ENUM('FUTURE','COMPLETED') NOT NULL DEFAULT 'FUTURE',
  user_limit      INT UNSIGNED,              
  latitude        DECIMAL(9,6),
  longitude       DECIMAL(9,6),
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
                  ON UPDATE CURRENT_TIMESTAMP,


  CONSTRAINT fk_events_owner
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
      ON UPDATE CASCADE ON DELETE RESTRICT,

  CONSTRAINT fk_events_type
     FOREIGN KEY (type_id) REFERENCES event_types(id)
       ON UPDATE CASCADE ON DELETE SET NULL,

  INDEX idx_events_owner (owner_user_id),
  INDEX idx_events_starts_at (starts_at),
  INDEX idx_events_status (status)
) ENGINE=InnoDB;

CREATE TABLE applications (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  event_id      BIGINT UNSIGNED NOT NULL,
  user_id       BIGINT UNSIGNED NOT NULL,
  why_me        TEXT,
  status        ENUM('PENDING','APPROVED') NOT NULL DEFAULT 'PENDING',

  CONSTRAINT fk_apps_event
    FOREIGN KEY (event_id) REFERENCES events(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  CONSTRAINT fk_apps_user
    FOREIGN KEY (user_id)  REFERENCES users(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  UNIQUE KEY uq_application_event_user (event_id, user_id),

  INDEX idx_applications_status (status)
) ENGINE=InnoDB;

CREATE TABLE participants (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  event_id        BIGINT UNSIGNED NOT NULL,
  user_id         BIGINT UNSIGNED NOT NULL,
  application_id  BIGINT UNSIGNED, 
  status          ENUM('ATTENDED','NO_SHOW') NOT NULL DEFAULT 'NO_SHOW',

  CONSTRAINT fk_participants_event
    FOREIGN KEY (event_id) REFERENCES events(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  CONSTRAINT fk_participants_user
    FOREIGN KEY (user_id) REFERENCES users(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  CONSTRAINT fk_participants_application
    FOREIGN KEY (application_id) REFERENCES applications(id)
      ON UPDATE CASCADE ON DELETE SET NULL,

  UNIQUE KEY uq_participant_event_user (event_id, user_id),

  INDEX idx_participants_status (status)
) ENGINE=InnoDB;


CREATE TABLE ratings (
  id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  event_id    BIGINT UNSIGNED NOT NULL,
  user_id     BIGINT UNSIGNED NOT NULL,
  rating      TINYINT UNSIGNED NOT NULL,
  comment     TEXT,


  CONSTRAINT fk_ratings_event
    FOREIGN KEY (event_id) REFERENCES events(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  CONSTRAINT fk_ratings_user
    FOREIGN KEY (user_id)  REFERENCES users(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  
  UNIQUE KEY uq_rating_event_user (event_id, user_id)

) ENGINE=InnoDB;

INSERT INTO universities (name) VALUES
  ('Istanbul Technical University'),
  ('Bogazici University'),
  ('Middle East Technical University'),
  ('Koc University'),
  ('Sabanci University'),
  ('Yildiz Technical University'),
  ('Bilkent University'),
  ('Ankara University'),
  ('Ege University'),
  ('Hacettepe University');

INSERT INTO users (name, username, email, password_hash, photo_url, latitude, longitude, role, university_id)
VALUES
  ('Onat Budak', 'onat', 'onat@example.com', 'hash1', NULL, 41.1050, 29.0250, 'USER', 1),
  ('Ada Lovelace', 'ada', 'ada@example.com', 'hash2', NULL, 41.0853, 29.0434, 'ADMIN', 1),
  ('Grace Hopper', 'grace', 'grace@example.com', 'hash3', NULL, 39.9334, 32.8597, 'USER', 3),
  ('Alan Turing', 'alant', 'turing@example.com', 'hash4', NULL, 51.5074, -0.1278, 'USER', 2),
  ('Linus Torvalds', 'linus', 'linus@example.com', 'hash5', NULL, 60.1699, 24.9384, 'USER', 5),
  ('Elon Musk', 'elon', 'elon@example.com', 'hash6', NULL, 34.0522, -118.2437, 'USER', 4),
  ('Mark Zuckerberg', 'markz', 'mark@example.com', 'hash7', NULL, 37.4848, -122.1484, 'USER', 6),
  ('Bill Gates', 'billg', 'bill@example.com', 'hash8', NULL, 47.6062, -122.3321, 'USER', 7),
  ('Steve Jobs', 'jobs', 'jobs@example.com', 'hash9', NULL, 37.3348, -122.0090, 'USER', 4),
  ('Dennis Ritchie', 'dennis', 'dennis@example.com', 'hash10', NULL, 40.7128, -74.0060, 'USER', 2);


INSERT INTO event_types (code) VALUES
 ('TECH'),
 ('MUSIC'),
 ('PARTY'),
 ('EDUCATION'),
 ('SPORTS'),
 ('GAME'),
 ('CAREER'),
 ('SEMINAR'),
 ('BUSINESS'),
 ('SOCIAL');

INSERT INTO events (
  owner_user_id, title, explanation, type_id, price,
  starts_at, ends_at, location_name, photo_url,
  status, user_limit, latitude, longitude, created_at, updated_at
)
VALUES
  (1, 'Tech Meetup', 'Monthly ITU tech meetup', 1, 0,
   '2025-01-10 18:00:00', '2025-01-10 21:00:00', 'ITU Ayazağa Kampüsü, SDKM', NULL,
   'FUTURE', 50, 41.1050, 29.0250, NOW(), NOW()),

  (2, 'Jazz Night', 'Chill jazz music night', 2, 50,
   '2025-02-12 20:00:00', '2025-02-12 23:30:00', 'Bogazici University, Albert Long Hall', NULL,
   'FUTURE', 100, 41.0892, 29.0501, NOW(), NOW()),

  (3, 'Chess Tournament', 'Open Swiss chess tournament', 6, 20,
   '2025-03-05 10:00:00', '2025-03-05 18:00:00', 'METU Culture and Convention Center', NULL,
   'FUTURE', 40, 39.9334, 32.8597, NOW(), NOW()),

  (4, 'AI Seminar', 'Turing on machine learning', 8, 0,
   '2025-04-01 15:00:00', '2025-04-01 17:00:00', 'University College London, Hall A', NULL,
   'FUTURE', 200, 51.5074, -0.1278, NOW(), NOW()),

  (5, 'Linux Workshop', 'Kernel development basics', 4, 15,
   '2025-03-22 13:00:00', '2025-03-22 16:00:00', 'Kumpula Campus, Helsinki University', NULL,
   'FUTURE', 30, 60.1699, 24.9384, NOW(), NOW()),

  (6, 'Startup Pitch', 'Elon hosts pitch event', 10, 0,
   '2025-02-01 19:00:00', '2025-02-01 22:00:00', 'Silicon Valley Innovation Hub', NULL,
   'FUTURE', 500, 34.0522, -118.2437, NOW(), NOW()),

  (7, 'Hackathon', '48-hour hackathon', 1, 0,
   '2025-05-10 09:00:00', '2025-05-12 09:00:00', 'Facebook HQ, Menlo Park', NULL,
   'FUTURE', 150, 37.4848, -122.1484, NOW(), NOW()),

  (8, 'Charity Marathon', 'Run for education', 5, 25,
   '2025-06-15 08:00:00', '2025-06-15 12:00:00', 'Seattle City Marathon Route', NULL,
   'FUTURE', 1000, 47.6062, -122.3321, NOW(), NOW()),

  (9, 'iOS Dev Talk', 'SwiftUI workshop', 4, 10,
   '2025-07-01 10:00:00', '2025-07-01 13:00:00', 'Apple Park Auditorium', NULL,
   'FUTURE', 80, 37.3348, -122.0090, NOW(), NOW()),

  (10, 'C Programming', 'Dennis explains pointers', 4, 5,
   '2025-02-20 11:00:00', '2025-02-20 13:00:00', 'New York Tech Hub', NULL,
   'FUTURE', 60, 40.7128, -74.0060, NOW(), NOW());


INSERT INTO applications (event_id, user_id, why_me, status)
VALUES
 (1, 2, 'I love tech events', 'APPROVED'),
 (1, 3, 'Interested in networking', 'PENDING'),
 (2, 4, 'Jazz enthusiast', 'APPROVED'),
 (2, 5, 'Love music', 'PENDING'),
 (3, 6, 'Chess player', 'APPROVED'),
 (3, 7, 'Want to improve chess skills', 'PENDING'),
 (4, 8, 'AI researcher', 'APPROVED'),
 (5, 9, 'Linux fan', 'APPROVED'),
 (6, 10, 'Startup founder', 'APPROVED'),
 (7, 3, 'Hackathon lover', 'PENDING');

INSERT INTO participants (event_id, user_id, application_id, status)
VALUES
 (1, 2, 1, 'ATTENDED'),
 (2, 4, 3, 'ATTENDED'),
 (3, 6, 5, 'NO_SHOW'),
 (4, 8, 7, 'ATTENDED'),
 (5, 9, 8, 'ATTENDED'),
 (6, 10, 9, 'ATTENDED'),
 (7, 3, 10, 'NO_SHOW'),
 (1, 3, 2, 'NO_SHOW'),
 (2, 5, 4, 'ATTENDED'),
 (3, 7, 6, 'ATTENDED');


INSERT INTO ratings (event_id, user_id, rating, comment)
VALUES
 (1, 2, 5, 'Great event!'),
 (2, 4, 4, 'Nice music'),
 (3, 6, 3, 'Could be better organized'),
 (4, 8, 5, 'Amazing talk!'),
 (5, 9, 4, 'Very helpful workshop'),
 (6, 10, 5, 'Loved the pitches'),
 (7, 3, 4, 'Fun hackathon'),
 (2, 5, 3, 'It was okay'),
 (1, 3, 4, 'Good networking'),
 (3, 7, 5, 'Loved the tournament');



