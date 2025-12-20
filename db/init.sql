
CREATE TABLE universities (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name          VARCHAR(200) NOT NULL,
  UNIQUE KEY uq_university_name (name)
) ENGINE=InnoDB;

CREATE TABLE university_domains (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  university_id BIGINT UNSIGNED NOT NULL, 
  domain        VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL, 
  
  UNIQUE KEY uq_domain (domain), 

  FOREIGN KEY (university_id) REFERENCES universities (id) ON DELETE CASCADE 
) ENGINE=InnoDB;

CREATE TABLE users (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name            VARCHAR(120) NOT NULL,
  username        VARCHAR(60)  NOT NULL,
  email           VARCHAR(256) NOT NULL,
  password_hash   VARCHAR(255) NOT NULL,   
  photo_url       VARCHAR(500),              
  latitude        DECIMAL(9,6),              
  longitude       DECIMAL(9,6),
  role            ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
  status          INTEGER NOT NULL DEFAULT 0,
  university_id   BIGINT UNSIGNED,
  reset_password_expires DATETIME NULL,
  reset_password_token   VARCHAR(100) NULL,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_blocked      BOOLEAN DEFAULT FALSE,
  gender          ENUM('MALE','FEMALE') NOT NULL,


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


CREATE TABLE organizations (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name            VARCHAR(200) NOT NULL,
  description     TEXT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  owner_user_id   BIGINT UNSIGNED NOT NULL,  -- e.g., club representative or admin
  photo_url       VARCHAR(500),
  status          ENUM('ACTIVE','INACTIVE') DEFAULT 'ACTIVE',

  CONSTRAINT fk_org_owner FOREIGN KEY (owner_user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE CASCADE,

  UNIQUE KEY uq_org_name (name)
) ENGINE=InnoDB;


CREATE TABLE events (
    id                       BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,

    owner_user_id            BIGINT UNSIGNED NOT NULL,
    owner_type               ENUM('USER', 'ORGANIZATION') NOT NULL DEFAULT 'USER',
    owner_organization_id    BIGINT UNSIGNED NULL,

    title                    VARCHAR(200) NOT NULL,
    explanation              TEXT NOT NULL,

    type_id                  BIGINT UNSIGNED,
    has_register             BOOLEAN NOT NULL DEFAULT 1,
    price                    DECIMAL(10,2) NOT NULL,

    starts_at                DATETIME NOT NULL,
    ends_at                  DATETIME,

    location_name            VARCHAR(500),
    photo_url                VARCHAR(500),

    status                   ENUM(
                                 'DRAFT',
                                 'PENDING_REVIEW',
                                 'FUTURE',
                                 'COMPLETED',
                                 'REJECTED'
                             ) NOT NULL DEFAULT 'DRAFT',

    review_reason            TEXT NULL,
    review_flags             JSON NULL,
    review_source            ENUM('AI','ADMIN') NULL,
    reviewed_by              BIGINT UNSIGNED NULL,
    reviewed_at              DATETIME NULL,

    admin_note               TEXT NULL,

    user_limit               INT UNSIGNED,
    latitude                 DECIMAL(9,6),
    longitude                DECIMAL(9,6),

    created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at               DATETIME DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,

    is_participants_private  BOOLEAN NOT NULL DEFAULT 0,
    only_girls               BOOLEAN NOT NULL DEFAULT 0,

    CONSTRAINT fk_events_owner_user
        FOREIGN KEY (owner_user_id)
        REFERENCES users(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_events_owner_org
        FOREIGN KEY (owner_organization_id)
        REFERENCES organizations(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    CONSTRAINT fk_events_type
        FOREIGN KEY (type_id)
        REFERENCES event_types(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    CONSTRAINT fk_events_reviewed_by
        FOREIGN KEY (reviewed_by)
        REFERENCES users(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    INDEX idx_events_owner_user (owner_user_id),
    INDEX idx_events_owner_org  (owner_organization_id),
    INDEX idx_events_starts_at  (starts_at),
    INDEX idx_events_status     (status)

) ENGINE=InnoDB;


CREATE TABLE applications (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  event_id      BIGINT UNSIGNED NOT NULL,
  user_id       BIGINT UNSIGNED NOT NULL,
  why_me        TEXT,
  status        ENUM('PENDING','APPROVED','REJECTED') NOT NULL DEFAULT 'PENDING',

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
  ticket_code     VARCHAR(36) NOT NULL UNIQUE,

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

CREATE TABLE organization_members (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  organization_id BIGINT UNSIGNED NOT NULL,
  user_id         BIGINT UNSIGNED NOT NULL,
  role            ENUM('ADMIN','MEMBER','REPRESENTATIVE') DEFAULT 'MEMBER',
  joined_at       DATETIME DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_org_members_org FOREIGN KEY (organization_id) REFERENCES organizations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_org_members_user FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE CASCADE,

  UNIQUE KEY uq_org_member (organization_id, user_id)
) ENGINE=InnoDB;

CREATE TABLE organization_applications (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  organization_id BIGINT UNSIGNED NOT NULL,
  user_id         BIGINT UNSIGNED NOT NULL,
  motivation      TEXT,
  status          ENUM('PENDING','APPROVED','REJECTED') DEFAULT 'PENDING',
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_org_app_org FOREIGN KEY (organization_id) REFERENCES organizations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_org_app_user FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE CASCADE,

  UNIQUE KEY uq_org_application (organization_id, user_id)
) ENGINE=InnoDB;

CREATE TABLE reports (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  event_id        BIGINT UNSIGNED NOT NULL,
  reporter_user_id BIGINT UNSIGNED NOT NULL,
  reason          TEXT NOT NULL,
  status          ENUM('PENDING','ACCEPTED','REJECTED') DEFAULT 'PENDING',
  is_reviewed     BOOLEAN DEFAULT FALSE,
  admin_notes     TEXT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_reports_event FOREIGN KEY (event_id) REFERENCES events(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_reports_user FOREIGN KEY (reporter_user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
    
  INDEX idx_reports_status (status),
  INDEX idx_reports_is_reviewed (is_reviewed),
  INDEX idx_reports_created (created_at)
) ENGINE=InnoDB;




INSERT INTO universities (name) VALUES
  ('Abdullah Gul University'),
  ('Abant Izzet Baysal University'),
  ('Acibadem University'),
  ('Adana Science and Technology University'),
  ('Adiyaman University'),
  ('Adnan Menderes University'),
  ('Agri Ibrahim Cecen University'),
  ('Ahi Evran University'),
  ('Air Force Academy'),
  ('Akdeniz University'),
  ('Aksaray University'),
  ('Alanya Alaaddin Keykubat University'),
  ('Alanya Hamdullah Emin Pasa University'),
  ('Amasya University'),
  ('Anadolu University'),
  ('Ankara Social Science University'),
  ('Ankara University'),
  ('Ankara Yildirim Beyazit University'),
  ('Antalya International University'),
  ('Ardahan University'),
  ('Artvin Coruh University'),
  ('Atatürk University'),
  ('Atilim University'),
  ('Avrasya University'),
  ('Bahcesehir University'),
  ('Balikesir University'),
  ('Bandirma ONYEDI Eylul University'),
  ('Bartin University'),
  ('Baskent University'),
  ('Batman University'),
  ('Bayburt University'),
  ('Beykent University'),
  ('Bezmialem Vakif University'),
  ('Bilecik University'),
  ('Bilkent University'),
  ('Bingol University'),
  ('Biruni University'),
  ('Bitlis Eren University'),
  ('Boğaziçi University'),
  ('Bozok University'),
  ('Bulent Ecevit University'),
  ('Bursa Technical University'),
  ('Cag University'),
  ('Canakkale (18th March) University'),
  ('Cankaya University'),
  ('Cankiri karatekin University'),
  ('Celal Bayar University'),
  ('Charisma University'),
  ('Cumhuriyet (Republik) University'),
  ('Cukurova University'),
  ('Dicle (Tirgris) University'),
  ('Dogus University'),
  ('Dokuz Eylül University'),
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
  ('International Turkmen Turkish University'),
  ('Inönü University'),
  ('Iskenderun Technical University'),
  ('Isik University'),
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
  ('Izmir Bakırçay University'),
  ('Izmir Democracy University'),
  ('Izmir Institute of Technology'),
  ('Izmir Katip Celebi University'),
  ('Izmir Tınaztepe University'),
  ('Izmir University of Economics'),
  ('Kafkas University'),
  ('Kahramanmaras Sütcü Imam University'),
  ('Karabuk University'),
  ('Karadeniz Technical University'),
  ('Karamanoglu Mehmet Bey University'),
  ('Kastamonu University'),
  ('Kilis 7 Aralık University'),
  ('Kirikkale University'),
  ('Kirklareli University'),
  ('Kocaeli University'),
  ('Konya Gida ve Tarim University'),
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
  ('Namik Kemal University'),
  ('Necmettin Erbakan University'),
  ('Nevsehir Haci Bektas Veli University'),
  ('Nisantasi University'),
  ('Nuh Naci Yazgan University'),
  ('OSTIM Technical University'),
  ('Okan University'),
  ('Omer Halisdemir University'),
  ('Ondokuz Mayis University Samsun'),
  ('Ordu University'),
  ('Osmaniye Korkut Ata University'),
  ('Osmangazi University'),
  ('Ozyegin University'),
  ('Pamukkale University'),
  ('Piri Reis University'),
  ('Recep Tayyip Erdogan University'),
  ('Sabanci University'),
  ('Sakarya University'),
  ('Sanko University'),
  ('Selcuk University'),
  ('Siirt University'),
  ('Sinop University'),
  ('Sirnak University'),
  ('Suleyman Demirel University'),
  ('TED University'),
  ('TOBB Economics and Technology University'),
  ('Tarsus University'),
  ('Toros University'),
  ('Trakya University'),
  ('Tunceli University'),
  ('Turkish Aeronautical Association University'),
  ('Turkish Naval Academy'),
  ('Türkisch-Deutsche Universität'),
  ('Ufuk University'),
  ('Uludag University'),
  ('University of Kyrenia'),
  ('Usak University'),
  ('Uskudar University'),
  ('Yalova University'),
  ('Yasar University'),
  ('Yeditepe University'),
  ('Yeni Yuzyil University'),
  ('Yildiz Technical University'),
  ('Yuksek Ihtisas University'),
  ('Yüzüncü Yil (Centennial) University'),
  ('Zonguldak Karaelmas University');

INSERT INTO university_domains (university_id, domain) VALUES
  (1, 'agu.edu.tr'),
  (2, 'ibu.edu.tr'),
  (3, 'acibadem.edu.tr'),
  (4, 'adanabtu.edu.tr'),
  (5, 'adiyaman.edu.tr'),
  (6, 'adu.edu.tr'),
  (7, 'agri.edu.tr'),
  (8, 'ahievran.edu.tr'),
  (9, 'hho.edu.tr'),
  (10, 'akdeniz.edu.tr'),
  (11, 'aksaray.edu.tr'),
  (12, 'alanyaaku.edu.tr'),
  (13, 'ahap.edu.tr'),
  (14, 'amasya.edu.tr'),
  (15, 'anadolu.edu.tr'),
  (16, 'asbu.edu.tr'),
  (17, 'ankara.edu.tr'),
  (18, 'aybu.edu.tr'),
  (19, 'antalya.edu.tr'),
  (20, 'ardahan.edu.tr'),
  (21, 'artvin.edu.tr'),
  (22, 'atauni.edu.tr'),
  (23, 'atilim.edu.tr'),
  (24, 'avrasya.edu.tr'),
  (25, 'bahcesehir.edu.tr'),
  (26, 'balikesir.edu.tr'),
  (27, 'bandirma.edu.tr'),
  (28, 'bartin.edu.tr'),
  (29, 'baskent.edu.tr'),
  (30, 'batman.edu.tr'),
  (31, 'bayburt.edu.tr'),
  (32, 'beykent.edu.tr'),
  (33, 'bezmialem.edu.tr'),
  (34, 'bilecik.edu.tr'),
  (35, 'bilkent.edu.tr'),
  (36, 'bingol.edu.tr'),
  (37, 'biruni.edu.tr'),
  (38, 'beu.edu.tr'),
  (39, 'boun.edu.tr'),
  (40, 'bozok.edu.tr'),
  (41, 'beun.edu.tr'),
  (42, 'btu.edu.tr'),
  (43, 'cag.edu.tr'),
  (44, 'comu.edu.tr'),
  (45, 'cankaya.edu.tr'),
  (46, 'karatekin.edu.tr'),
  (47, 'mcbu.edu.tr'),
  (47, 'cbu.edu.tr'),
  (48, 'charismauniversity.org'),
  (49, 'cumhuriyet.edu.tr'),
  (50, 'cu.edu.tr'),
  (51, 'dicle.edu.tr'),
  (52, 'dogus.edu.tr'),
  (53, 'deu.edu.tr'),
  (54, 'dumlupinar.edu.tr'),
  (54, 'dpu.edu.tr'),
  (55, 'duzce.edu.tr'),
  (56, 'ege.edu.tr'),
  (57, 'erciyes.edu.tr'),
  (58, 'ebyu.edu.tr'),
  (59, 'erzurum.edu.tr'),
  (60, 'eskisehir.edu.tr'),
  (61, 'fatihsultan.edu.tr'),
  (62, 'fbu.edu.tr'),
  (63, 'firat.edu.tr'),
  (64, 'gsu.edu.tr'),
  (65, 'gazi.edu.tr'),
  (66, 'gantep.edu.tr'),
  (67, 'gop.edu.tr'),
  (68, 'gyte.edu.tr'),
  (69, 'gtu.edu.tr'),
  (70, 'gedik.edu.tr'),
  (71, 'gata.edu.tr'),
  (72, 'gumushane.edu.tr'),
  (73, 'hacettepe.edu.tr'),
  (73, 'hun.edu.tr'),
  (74, 'hakkari.edu.tr'),
  (75, 'halic.edu.tr'),
  (76, 'harran.edu.tr'),
  (77, 'hku.edu.tr'),
  (78, 'sbu.edu.tr'),
  (79, 'hitit.edu.tr'),
  (80, 'igdir.edu.tr'),
  (81, 'ittu.edu.tm'),
  (82, 'inonu.edu.tr'),
  (83, 'iste.edu.tr'),
  (84, 'isikun.edu.tr'),
  (85, '29mayis.edu.tr'),
  (86, 'arel.edu.tr'),
  (87, 'aydin.edu.tr'),
  (88, 'bilgi.edu.tr'),
  (89, 'esenyurt.edu.tr'),
  (90, 'gelisim.edu.tr'),
  (91, 'kemerburgaz.edu.tr'),
  (92, 'iku.edu.tr'),
  (93, 'medeniyet.edu.tr'),
  (94, 'medipol.edu.tr'),
  (95, 'rumeli.edu.tr'),
  (96, 'iszu.edu.tr'),
  (97, 'sehir.edu.tr'),
  (98, 'itu.edu.tr'),
  (99, 'ticaret.edu.tr'),
  (99, 'istanbulticaret.edu.tr'),
  (100, 'istanbul.edu.tr'),
  (100, 'ogr.iu.edu.tr'),
  (101, 'bakircay.edu.tr'),
  (102, 'idu.edu.tr'),
  (103, 'iyte.edu.tr'),
  (104, 'ikc.edu.tr'),
  (104, 'ikcu.edu.tr'),
  (105, 'tinaztepe.edu.tr'),
  (106, 'ieu.edu.tr'),
  (106, 'izmirekonomi.edu.tr'),
  (107, 'kafkas.edu.tr'),
  (108, 'ksu.edu.tr'),
  (109, 'karabuk.edu.tr'),
  (110, 'ktu.edu.tr'),
  (111, 'kmu.edu.tr'),
  (112, 'kastamonu.edu.tr'),
  (113, 'kilis.edu.tr'),
  (114, 'kku.edu.tr'),
  (115, 'kirklareli.edu.tr'),
  (116, 'kou.edu.tr'),
  (117, 'gidatarim.edu.tr'),
  (118, 'ktun.edu.tr'),
  (119, 'ku.edu.tr'),
  (120, 'maltepe.edu.tr'),
  (121, 'artuklu.edu.tr'),
  (122, 'marmara.edu.tr'),
  (123, 'mef.edu.tr'),
  (124, 'mehmetakif.edu.tr'),
  (125, 'mersin.edu.tr'),
  (126, 'metu.edu.tr'),
  (127, 'msgsu.edu.tr'),
  (128, 'msu.edu.tr'),
  (129, 'mu.edu.tr'),
  (129, 'marun.edu.tr'),
  (130, 'alparslan.edu.tr'),
  (131, 'mku.edu.tr'),
  (132, 'nku.edu.tr'),
  (133, 'konya.edu.tr'),
  (134, 'nevsehir.edu.tr'),
  (135, 'nisantasi.edu.tr'),
  (136, 'nny.edu.tr'),
  (137, 'ostimteknik.edu.tr'),
  (138, 'okan.edu.tr'),
  (139, 'ohu.edu.tr'),
  (140, 'omu.edu.tr'),
  (141, 'odu.edu.tr'),
  (142, 'osmaniye.edu.tr'),
  (143, 'ogu.edu.tr'),
  (144, 'ozyegin.edu.tr'),
  (144, 'ozu.edu.tr'),
  (145, 'pamukkale.edu.tr'),
  (146, 'pirireis.edu.tr'),
  (147, 'erdogan.edu.tr'),
  (148, 'sabanciuniv.edu.tr'),
  (148, 'sabanciuniv.edu'),
  (149, 'sau.edu.tr'),
  (149, 'sakarya.edu.tr'),
  (150, 'sanko.edu.tr'),
  (151, 'selcuk.edu.tr'),
  (152, 'siirt.edu.tr'),
  (153, 'sinop.edu.tr'),
  (154, 'sirnak.edu.tr'),
  (155, 'sdu.edu.tr'),
  (156, 'tedu.edu.tr'),
  (157, 'etu.edu.tr'),
  (158, 'tarsus.edu.tr'),
  (159, 'toros.edu.tr'),
  (160, 'trakya.edu.tr'),
  (161, 'tunceli.edu.tr'),
  (162, 'thk.edu.tr'),
  (163, 'dho.edu.tr'),
  (164, 'tau.edu.tr'),
  (165, 'ufuk.edu.tr'),
  (166, 'uludag.edu.tr'),
  (167, 'std.kyrenia.edu.tr'),
  (167, 'kyrenia.edu.tr'),
  (168, 'usak.edu.tr'),
  (169, 'uskudar.edu.tr'),
  (170, 'yalova.edu.tr'),
  (171, 'yasar.edu.tr'),
  (172, 'yeditepe.edu.tr'),
  (173, 'yeniyuzyil.edu.tr'),
  (174, 'yildiz.edu.tr'),
  (175, 'yuksekihtisasuniversitesi.edu.tr'),
  (176, 'yyu.edu.tr'),
  (177, 'karaelmas.edu.tr');

INSERT INTO users (name, username, email, password_hash, photo_url, latitude, longitude, role, university_id)
VALUES
  ('Onat Budak', 'onat', 'onat@itu.edu.tr', 'hash1', NULL, 41.1050, 29.0250, 'USER', 1),
  ('Ada Lovelace', 'ada', 'ada@itu.edu.tr', 'hash2', NULL, 41.0853, 29.0434, 'ADMIN', 1),
  ('Grace Hopper', 'grace', 'grace@itu.edu.tr', 'hash3', NULL, 39.9334, 32.8597, 'USER', 3),
  ('Alan Turing', 'alant', 'turing@itu.edu.tr', 'hash4', NULL, 51.5074, -0.1278, 'USER', 2),
  ('Linus Torvalds', 'linus', 'linus@itu.edu.tr', 'hash5', NULL, 60.1699, 24.9384, 'USER', 5),
  ('Elon Musk', 'elon', 'elon@itu.edu.tr', 'hash6', NULL, 34.0522, -118.2437, 'USER', 4),
  ('Mark Zuckerberg', 'markz', 'mark@itu.edu.tr', 'hash7', NULL, 37.4848, -122.1484, 'USER', 6),
  ('Bill Gates', 'billg', 'bill@itu.edu.tr', 'hash8', NULL, 47.6062, -122.3321, 'USER', 7),
  ('Steve Jobs', 'jobs', 'jobs@itu.edu.tr', 'hash9', NULL, 37.3348, -122.0090, 'USER', 4),
  ('Dennis Ritchie', 'dennis', 'dennis@itu.edu.tr', 'hash10', NULL, 40.7128, -74.0060, 'USER', 2);


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

INSERT INTO organizations (name, description, owner_user_id, photo_url, status)
VALUES
  ('ITU AI Club', 'Artificial Intelligence enthusiasts from Istanbul Technical University.', 1, NULL, 'ACTIVE'),
  ('Bogazici Jazz Society', 'A student community for jazz music lovers.', 2, NULL, 'ACTIVE'),
  ('METU Chess Club', 'Competitive and casual chess community.', 3, NULL, 'ACTIVE'),
  ('Koc Entrepreneurship Club', 'Innovation and startup-oriented student group.', 5, NULL, 'ACTIVE'),
  ('Hacettepe Coding Society', 'Hacettepe students learning modern programming.', 10, NULL, 'ACTIVE');

INSERT INTO events (
  owner_user_id, owner_type, owner_organization_id,
  title, explanation, type_id, price,
  starts_at, ends_at, location_name, photo_url,
  status, user_limit, latitude, longitude, created_at, updated_at
)
VALUES 
  (1, 'USER', NULL, 'Tech Meetup', 'Monthly ITU tech meetup', 1, 0,
   '2024-12-10 18:00:00', '2024-12-10 21:00:00', 'ITU Ayazağa Kampüsü, SDKM', NULL,
   'COMPLETED', 50, 41.1050, 29.0250, NOW(), NOW()),

  (2, 'USER', NULL, 'Jazz Night', 'Chill jazz music night', 2, 50,
   '2025-02-12 20:00:00', '2025-02-12 23:30:00', 'Bogazici University, Albert Long Hall', NULL,
   'FUTURE', 100, 41.0892, 29.0501, NOW(), NOW()),

  (3, 'USER', NULL, 'Chess Tournament', 'Open Swiss chess tournament', 6, 20,
   '2025-03-05 10:00:00', '2025-03-05 18:00:00', 'METU Culture and Convention Center', NULL,
   'FUTURE', 40, 39.9334, 32.8597, NOW(), NOW()),

  (4, 'USER', NULL, 'AI Seminar', 'Turing on machine learning', 8, 0,
   '2024-11-15 15:00:00', '2024-11-15 17:00:00', 'University College London, Hall A', NULL,
   'COMPLETED', 200, 51.5074, -0.1278, NOW(), NOW()),

  (5, 'USER', NULL, 'Linux Workshop', 'Kernel development basics', 4, 15,
   '2025-03-22 13:00:00', '2025-03-22 16:00:00', 'Kumpula Campus, Helsinki University', NULL,
   'FUTURE', 30, 60.1699, 24.9384, NOW(), NOW()),

  (6, 'USER', NULL, 'Startup Pitch', 'Elon hosts pitch event', 10, 0,
   '2025-02-01 19:00:00', '2025-02-01 22:00:00', 'Silicon Valley Innovation Hub', NULL,
   'FUTURE', 500, 34.0522, -118.2437, NOW(), NOW()),

  (7, 'USER', NULL, 'Hackathon', '48-hour hackathon', 1, 0,
   '2025-05-10 09:00:00', '2025-05-12 09:00:00', 'Facebook HQ, Menlo Park', NULL,
   'FUTURE', 150, 37.4848, -122.1484, NOW(), NOW()),

  (8, 'USER', NULL, 'Charity Marathon', 'Run for education', 5, 25,
   '2024-10-15 08:00:00', '2024-10-15 12:00:00', 'Seattle City Marathon Route', NULL,
   'COMPLETED', 1000, 47.6062, -122.3321, NOW(), NOW()),

  (9, 'USER', NULL, 'iOS Dev Talk', 'SwiftUI workshop', 4, 10,
   '2025-07-01 10:00:00', '2025-07-01 13:00:00', 'Apple Park Auditorium', NULL,
   'FUTURE', 80, 37.3348, -122.0090, NOW(), NOW()),

  (10, 'USER', NULL, 'C Programming', 'Dennis explains pointers', 4, 5,
   '2025-02-20 11:00:00', '2025-02-20 13:00:00', 'New York Tech Hub', NULL,
   'FUTURE', 60, 40.7128, -74.0060, NOW(), NOW()),

  (1, 'ORGANIZATION', 1, 'AI Bootcamp', 'Deep learning bootcamp hosted by ITU AI Club', 4, 0,
   '2025-09-10 09:00:00', '2025-09-12 18:00:00', 'ITU AI Lab', NULL,
   'FUTURE', 100, 41.1055, 29.0258, NOW(), NOW()),

  (2, 'ORGANIZATION', 2, 'Jazz Improvisation Workshop', 'Bogazici Jazz Society presents a hands-on improvisation session', 2, 30,
   '2024-11-20 14:00:00', '2024-11-20 18:00:00', 'Bogazici University Music Hall', NULL,
   'COMPLETED', 40, 41.0899, 29.0512, NOW(), NOW()),

  (3, 'ORGANIZATION', 3, 'METU Blitz Cup', 'Chess Club monthly blitz tournament', 6, 10,
   '2025-04-05 10:00:00', '2025-04-05 14:00:00', 'METU Student Center', NULL,
   'FUTURE', 60, 39.9330, 32.8601, NOW(), NOW()),

  (5, 'ORGANIZATION', 4, 'Startup Fair 2025', 'Koc Entrepreneurship Club startup showcase', 10, 0,
   '2025-11-05 10:00:00', '2025-11-05 17:00:00', 'Koc University Main Hall', NULL,
   'FUTURE', 300, 41.2000, 29.0150, NOW(), NOW()),

  (10, 'ORGANIZATION', 5, 'Hack the Future', 'Hacettepe Coding Society annual hackathon', 1, 0,
   '2025-10-25 09:00:00', '2025-10-27 18:00:00', 'Hacettepe University Tech Center', NULL,
   'FUTURE', 250, 39.9331, 32.8596, NOW(), NOW());
  

INSERT INTO organization_members (organization_id, user_id, role, joined_at)
VALUES
  (1, 1, 'ADMIN', NOW()),       
  (1, 3, 'MEMBER', NOW()),      
  (1, 4, 'MEMBER', NOW()),      
  (1, 5, 'REPRESENTATIVE', NOW()),

  (2, 2, 'ADMIN', NOW()),       
  (2, 4, 'MEMBER', NOW()),
  (2, 5, 'MEMBER', NOW()),
  (2, 6, 'REPRESENTATIVE', NOW()),

  (3, 3, 'ADMIN', NOW()),      
  (3, 6, 'MEMBER', NOW()),
  (3, 7, 'MEMBER', NOW()),

  (4, 5, 'ADMIN', NOW()),      
  (4, 6, 'REPRESENTATIVE', NOW()),
  (4, 7, 'MEMBER', NOW()),
  (4, 8, 'MEMBER', NOW()),


  (5, 10, 'ADMIN', NOW()),    
  (5, 8, 'MEMBER', NOW()),
  (5, 9, 'REPRESENTATIVE', NOW()),
  (5, 1, 'MEMBER', NOW());

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

INSERT INTO participants (event_id, user_id, application_id, status, ticket_code)
VALUES
 (1, 2, 1, 'ATTENDED', '10000000-0000-0000-0000-000000000001'),
 (2, 4, 3, 'ATTENDED', '10000000-0000-0000-0000-000000000002'),
 (3, 6, 5, 'NO_SHOW',  '10000000-0000-0000-0000-000000000003'),
 (4, 8, 7, 'ATTENDED', '10000000-0000-0000-0000-000000000004'),
 (5, 9, 8, 'ATTENDED', '10000000-0000-0000-0000-000000000005'),
 (6, 10, 9, 'ATTENDED', '10000000-0000-0000-0000-000000000006'),
 (7, 3, 10, 'NO_SHOW',  '10000000-0000-0000-0000-000000000007'),
 (1, 3, 2, 'NO_SHOW',  '10000000-0000-0000-0000-000000000008'),
 (2, 5, 4, 'ATTENDED', '10000000-0000-0000-0000-000000000009'),
 (3, 7, 6, 'ATTENDED', '10000000-0000-0000-0000-000000000010');


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

INSERT INTO organization_applications (organization_id, user_id, motivation, status, created_at)
VALUES
  (1, 6, 'I want to contribute to AI projects.', 'PENDING', NOW()),
  (2, 8, 'Jazz is my passion; I play saxophone.', 'APPROVED', NOW()),
  (3, 9, 'Chess is my hobby since childhood.', 'APPROVED', NOW()),
  (4, 2, 'Interested in startups and innovation.', 'PENDING', NOW()),
  (5, 4, 'Love coding and mentoring students.', 'APPROVED', NOW()),
  (1, 7, 'Excited about machine learning events.', 'PENDING', NOW());

INSERT INTO reports (event_id, reporter_user_id, reason, status, is_reviewed, admin_notes, created_at)
VALUES
  (1, 3, 'Event content is inappropriate and misleading', 'PENDING', FALSE, NULL, NOW()),
  (2, 5, 'Misleading event description, not what was advertised', 'ACCEPTED', TRUE, 'Event has been reviewed and removed', DATE_SUB(NOW(), INTERVAL 2 DAY)),
  (3, 7, 'This looks like a spam event', 'REJECTED', TRUE, 'Event is legitimate, verified with organizers', DATE_SUB(NOW(), INTERVAL 5 DAY)),
  (4, 2, 'Offensive language in event details', 'PENDING', FALSE, NULL, DATE_SUB(NOW(), INTERVAL 1 DAY)),
  (5, 6, 'Duplicate event already exists', 'ACCEPTED', TRUE, 'Duplicate removed, original kept', DATE_SUB(NOW(), INTERVAL 3 DAY)),
  (6, 4, 'Event violates community guidelines', 'PENDING', FALSE, NULL, DATE_SUB(NOW(), INTERVAL 6 HOUR)),
  (7, 8, 'Inappropriate content for student audience', 'REJECTED', TRUE, 'Content reviewed, found appropriate', DATE_SUB(NOW(), INTERVAL 1 WEEK));