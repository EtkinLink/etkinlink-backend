
CREATE TABLE universities (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name          VARCHAR(200) NOT NULL,
  UNIQUE KEY uq_university_name (name)
) ENGINE=InnoDB;

CREATE TABLE university_domains (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  university_id BIGINT UNSIGNED NOT NULL, 
  domain        VARCHAR(100) NOT NULL, 
  
  UNIQUE KEY uq_domain (domain), 

  FOREIGN KEY (university_id) REFERENCES universities (id) ON DELETE CASCADE 
) ENGINE=InnoDB;

CREATE TABLE users (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name            VARCHAR(120) NOT NULL,
  username        VARCHAR(60)  NOT NULL,
  email           VARCHAR(256) NOT NULL,
  password_hash   CHAR(255) NOT NULL,   
  photo_url       VARCHAR(500),              
  latitude        DECIMAL(9,6),              
  longitude       DECIMAL(9,6),
  role            ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
  status          INTEGER NOT NULL DEFAULT 0,
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
  ('Abdullah Gul University'),
  ('Acibadem University'),
  ('Adana Science and Technology University'),
  ('Adiyaman University'),
  ('Adnan Menderes University'),
  ('Agri Ibrahim Cecen University'),
  ('Ahi Evran University'),
  ('Akdeniz University'),
  ('Aksaray University'),
  ('Alanya Alaaddin Keykubat University'),
  ('Alanya Hamdullah Emin Pasa University'),
  ('Amasya University'),
  ('Anadolu University'),
  ('Ankara Medipol University'),
  ('Ankara Science University'),
  ('Ankara Social Science University'),
  ('Ankara University'),
  ('Ankara Yildirim Beyazit University'),
  ('Ardahan University'),
  ('Artvin Coruh University'),
  ('Atatürk University'),
  ('Avrasya University'),
  ('Bahcesehir University'),
  ('Balikesir University'),
  ('Bandirma ONYEDI Eylul University'),
  ('Bartin University'),
  ('Baskent University'),
  ('Batman University'),
  ('Bayburt University'),
  ('Bezmialem Vakif University'),
  ('Bilecik University'),
  ('Bilkent University'),
  ('Bingol University'),
  ('Biruni University'),
  ('Bitlis Eren University'),
  ('Boğaziçi University'),
  ('Bozok University'),
  ('Bursa Technical University'),
  ('Cag University'),
  ('Canakkale (18th March) University'),
  ('Cankaya University'),
  ('Cankiri karatekin University'),
  ('Celal Bayar University'),
  ('Cumhuriyet (Republik) University'),
  ('Cukurova University'),
  ('Dicle (Tirgris) University'),
  ('Dokuz Eylül University'),
  ('Dogus University'),
  ('Dumlupinar University'),
  ('Duzce University'),
  ('Ege University'),
  ('Erciyes University'),
  ('Erzincan Binali Yildirim University'),
  ('Erzurum Technical University'),
  ('Eskişehir Teknik Üniversitesi'),
  ('Fatih Sultan Mehmet University'),
  ('Fenerbahce University'),
  ('Firat (Euphrates) University'),
  ('Galatasaray University'),
  ('Gazi University Ankara'),
  ('Gaziantep University'),
  ('Gaziosmanpasa University'),
  ('Gebze Institute of Technology'),
  ('Gebze Technical University'),
  ('Gedik University'),
  ('Gulhane Military Medical Academy'),
  ('Gumushane University'),
  ('Hacettepe University'),
  ('Hakkari University'),
  ('Halic University'),
  ('Harran University'),
  ('Hasan Kalyoncu University'),
  ('Health Sciences University'),
  ('Hitit University'),
  ('Igdir University'),
  ('Inönü University'),
  ('Iskenderun Technical University'),
  ('Istanbul 29 Mayis University'),
  ('Istanbul Arel University'),
  ('Istanbul Aydin University'),
  ('Istanbul Bilgi University'),
  ('Istanbul Esenyurt University'),
  ('Istanbul Gelisim University'),
  ('Istanbul Kemerburgaz University'),
  ('Istanbul Kultur University'),
  ('Istanbul Medeniyet University'),
  ('Istanbul Medipol University'),
  ('Istanbul Rumeli University'),
  ('Istanbul Sabahattin Zaim University'),
  ('Istanbul Sehir University'),
  ('Istanbul Technical University'),
  ('Istanbul Ticaret University'),
  ('Istanbul University'),
  ('Isik University'),
  ('Izmir Bakırçay University'),
  ('Izmir Democracy University'),
  ('Izmir Institute of Technology'),
  ('Izmir Katip Celebi University'),
  ('Izmir Tınaztepe University'),
  ('Izmir University of Economics'),
  ('Kafkas University'),
  ('Kadir Has University'),
  ('Karabuk University'),
  ('karamanoglu mehmet bey University'),
  ('Kastamonu University'),
  ('Kilis 7 Aralık University'),
  ('Kirikkale University'),
  ('Kirklareli University'),
  ('Kocaeli University'),
  ('Konya Gida Tarim University'),
  ('Konya Technical University'),
  ('Koç University'),
  ('Maltepe University'),
  ('Mardin Artuklu University'),
  ('Marmara University'),
  ('MEF University'),
  ('Mehmet Akif Ersoy University'),
  ('Mersin University'),
  ('Middle East Technical University'),
  ('Mimar Sinan Fine Arts University'),
  ('Mimar Sinan University'),
  ('Mugla Sitki Kocman University'),
  ('Mus Alparslan University'),
  ('Mustafa Kemal University'),
  ('Necmettin Erbakan University'),
  ('Nevsehir Haci Bektas Veli University'),
  ('Nisantasi University'),
  ('Nuh Naci Yazgan University'),
  ('OSTIM Technical University'),
  ('Okan University'),
  ('Omer Halisdemir University'),
  ('Ondokuz Mayis University'),
  ('Osmaniye Korkut Ata University'),
  ('Ozyegin University'),
  ('Pamukkale University'),
  ('Piri Reis University'),
  ('Recep Tayip Erdogan University'),
  ('Sabanci University'),
  ('Sakarya University'),
  ('Sanko University'),
  ('Selcuk University'),
  ('Siirt University'),
  ('Sinop University'),
  ('Sirnak University'),
  ('Suleyman Demirel University'),
  ('TED University'),
  ('Tarsus University'),
  ('Tobb Economics and Technology University'),
  ('Toros University'),
  ('Trakya University'),
  ('Tunceli University'),
  ('Turkish Aeronautical Association University'),
  ('Turkish Naval Academy'),
  ('Türk Hava Kurumu Üniversitesi'),
  ('Türkisch-Deutsche Universität'),
  ('Ufuk University'),
  ('University of Kyrenia'),
  ('University of Turkish Aeronautical Association'),
  ('Usak University'),
  ('Uskudar University'),
  ('Yalova University'),
  ('Yasar University'),
  ('Yeditepe University'),
  ('Yeni Yuzyil University'),
  ('Yildirim Beyazit University'),
  ('Yildiz Technical University'),
  ('Yuksek ihtisas University'),
  ('Yüzüncü Yil (Centennial) University'),
  ('Zonguldak Karaelmas University');

INSERT INTO university_domains (university_id, domain) VALUES
  (1, 'agu.edu.tr'),
  (2, 'acibadem.edu.tr'),
  (3, 'adanabtu.edu.tr'),
  (4, 'adiyaman.edu.tr'),
  (5, 'adu.edu.tr'),
  (6, 'agri.edu.tr'),
  (7, 'ahievran.edu.tr'),
  (8, 'akdeniz.edu.tr'),
  (9, 'aksaray.edu.tr'),
  (10, 'alanyaaku.edu.tr'),
  (11, 'ahap.edu.tr'),
  (12, 'amasya.edu.tr'),
  (13, 'anadolu.edu.tr'),
  (14, 'ankaramedipol.edu.tr'),
  (15, 'ankarabilim.edu.tr'),
  (16, 'asbu.edu.tr'),
  (17, 'ankara.edu.tr'),
  (18, 'aybu.edu.tr'),
  (19, 'ardahan.edu.tr'),
  (20, 'artvin.edu.tr'),
  (21, 'atauni.edu.tr'),
  (22, 'avrasya.edu.tr'),
  (23, 'bahcesehir.edu.tr'),
  (24, 'balikesir.edu.tr'),
  (25, 'bandirma.edu.tr'),
  (26, 'bartin.edu.tr'),
  (27, 'baskent.edu.tr'),
  (28, 'batman.edu.tr'),
  (29, 'bayburt.edu.tr'),
  (30, 'bezmialem.edu.tr'),
  (31, 'bilecik.edu.tr'),
  (32, 'bilkent.edu.tr'),
  (33, 'bingol.edu.tr'),
  (34, 'biruni.edu.tr'),
  (35, 'beu.edu.tr'),
  (36, 'boun.edu.tr'),
  (37, 'bozok.edu.tr'),
  (38, 'btu.edu.tr'),
  (39, 'cag.edu.tr'),
  (40, 'comu.edu.tr'),
  (41, 'cankaya.edu.tr'),
  (42, 'karatekin.edu.tr'),
  (43, 'mcbu.edu.tr'),
  (43, 'cbu.edu.tr'),
  (44, 'cumhuriyet.edu.tr'),
  (45, 'cu.edu.tr'),
  (46, 'dicle.edu.tr'),
  (47, 'deu.edu.tr'),
  (48, 'dogus.edu.tr'),
  (49, 'dumlupinar.edu.tr'),
  (49, 'dpu.edu.tr'),
  (50, 'duzce.edu.tr'),
  (51, 'ege.edu.tr'),
  (52, 'erciyes.edu.tr'),
  (53, 'ebyu.edu.tr'),
  (54, 'erzurum.edu.tr'),
  (55, 'eskisehir.edu.tr'),
  (56, 'fatihsultan.edu.tr'),
  (57, 'fbu.edu.tr'),
  (58, 'firat.edu.tr'),
  (59, 'gsu.edu.tr'),
  (60, 'gazi.edu.tr'),
  (61, 'gantep.edu.tr'),
  (62, 'gop.edu.tr'),
  (63, 'gyte.edu.tr'),
  (64, 'gtu.edu.tr'),
  (65, 'gedik.edu.tr'),
  (66, 'gata.edu.tr'),
  (67, 'gumushane.edu.tr'),
  (68, 'hacettepe.edu.tr'),
  (68, 'hun.edu.tr'),
  (69, 'hakkari.edu.tr'),
  (70, 'halic.edu.tr'),
  (71, 'harran.edu.tr'),
  (72, 'hku.edu.tr'),
  (73, 'sbu.edu.tr'),
  (74, 'hitit.edu.tr'),
  (75, 'igdir.edu.tr'),
  (76, 'inonu.edu.tr'),
  (77, 'iste.edu.tr'),
  (78, '29mayis.edu.tr'),
  (79, 'arel.edu.tr'),
  (80, 'aydin.edu.tr'),
  (81, 'bilgi.edu.tr'),
  (82, 'esenyurt.edu.tr'),
  (83, 'gelisim.edu.tr'),
  (84, 'kemerburgaz.edu.tr'),
  (85, 'iku.edu.tr'),
  (86, 'medeniyet.edu.tr'),
  (87, 'medipol.edu.tr'),
  (88, 'rumeli.edu.tr'),
  (89, 'iszu.edu.tr'),
  (90, 'sehir.edu.tr'),
  (91, 'itu.edu.tr'),
  (92, 'ticaret.edu.tr'),
  (92, 'istanbulticaret.edu.tr'),
  (93, 'istanbul.edu.tr'),
  (93, 'ogr.iu.edu.tr'),
  (94, 'isikun.edu.tr'),
  (95, 'bakircay.edu.tr'),
  (96, 'idu.edu.tr'),
  (97, 'iyte.edu.tr'),
  (98, 'ikc.edu.tr'),
  (98, 'ikcu.edu.tr'),
  (99, 'tinaztepe.edu.tr'),
  (100, 'ieu.edu.tr'),
  (100, 'izmirekonomi.edu.tr'),
  (101, 'kafkas.edu.tr'),
  (102, 'khas.edu.tr'),
  (103, 'karabuk.edu.tr'),
  (104, 'kmu.edu.tr'),
  (105, 'kastamonu.edu.tr'),
  (106, 'kilis.edu.tr'),
  (107, 'kku.edu.tr'),
  (108, 'kirklareli.edu.tr'),
  (109, 'kou.edu.tr'),
  (110, 'gidatarim.edu.tr'),
  (111, 'ktun.edu.tr'),
  (112, 'ku.edu.tr'),
  (113, 'maltepe.edu.tr'),
  (114, 'artuklu.edu.tr'),
  (115, 'marmara.edu.tr'),
  (116, 'mef.edu.tr'),
  (117, 'mehmetakif.edu.tr'),
  (118, 'mersin.edu.tr'),
  (119, 'metu.edu.tr'),
  (120, 'msgsu.edu.tr'),
  (121, 'msu.edu.tr'),
  (122, 'mu.edu.tr'),
  (122, 'marun.edu.tr'),
  (123, 'alparslan.edu.tr'),
  (124, 'mku.edu.tr'),
  (125, 'konya.edu.tr'),
  (126, 'nevsehir.edu.tr'),
  (127, 'nisantasi.edu.tr'),
  (128, 'nny.edu.tr'),
  (129, 'ostimteknik.edu.tr'),
  (130, 'okan.edu.tr'),
  (131, 'ohu.edu.tr'),
  (132, 'omu.edu.tr'),
  (133, 'osmaniye.edu.tr'),
  (134, 'ozyegin.edu.tr'),
  (134, 'ozu.edu.tr'),
  (135, 'pamukkale.edu.tr'),
  (136, 'pirireis.edu.tr'),
  (137, 'erdogan.edu.tr'),
  (138, 'sabanciuniv.edu.tr'),
  (138, 'sabanciuniv.edu'),
  (139, 'sau.edu.tr'),
  (139, 'sakarya.edu.tr'),
  (140, 'sanko.edu.tr'),
  (141, 'selcuk.edu.tr'),
  (142, 'siirt.edu.tr'),
  (143, 'sinop.edu.tr'),
  (144, 'sirnak.edu.tr'),
  (145, 'sdu.edu.tr'),
  (146, 'tedu.edu.tr'),
  (147, 'tarsus.edu.tr'),
  (148, 'etu.edu.tr'),
  (149, 'toros.edu.tr'),
  (150, 'trakya.edu.tr'),
  (151, 'tunceli.edu.tr'),
  (152, 'thk.edu.tr'),
  (153, 'dho.edu.tr'),
  (154, 'thk.edu.tr'),
  (155, 'tau.edu.tr'),
  (156, 'ufuk.edu.tr'),
  (157, 'std.kyrenia.edu.tr'),
  (157, 'kyrenia.edu.tr'),
  (158, 'thk.edu.tr'),
  (159, 'usak.edu.tr'),
  (160, 'uskudar.edu.tr'),
  (161, 'yalova.edu.tr'),
  (162, 'yasar.edu.tr'),
  (163, 'yeditepe.edu.tr'),
  (164, 'yeniyuzyil.edu.tr'),
  (165, 'ybu.edu.tr'),
  (166, 'yildiz.edu.tr'),
  (167, 'yuksekihtisasuniversitesi.edu.tr'),
  (168, 'yyu.edu.tr'),
  (169, 'karaelmas.edu.tr');

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



