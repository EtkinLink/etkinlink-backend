DROP TABLE IF EXISTS ratings, participants, applications, events, event_types, users, universities;

CREATE TABLE universities (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name          VARCHAR(200) NOT NULL,
  domain_suffix VARCHAR(100) NOT NULL,
  UNIQUE KEY uq_university_name (name),
  UNIQUE KEY uq_university_domain (domain_suffix)
) ENGINE=InnoDB;


CREATE TABLE users (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name            VARCHAR(120) NOT NULL,
  username        VARCHAR(60)  NOT NULL,
  email           VARCHAR(254) NOT NULL,
  password_hash   VARCHAR(60) NOT NULL,   
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

INSERT INTO universities (name, domain_suffix) VALUES
  ('Adana Alparslan Türkeş Bilim ve Teknoloji Üniversitesi', 'atu.edu.tr'),
  ('Çukurova Üniversitesi', 'cu.edu.tr'),
  ('Adıyaman Üniversitesi', 'adiyaman.edu.tr'),
  ('Afyon Kocatepe Üniversitesi', 'aku.edu.tr'),
  ('Afyonkarahisar Sağlık Bilimleri Üniversitesi', 'afsu.edu.tr'),
  ('Ağrı İbrahim Çeçen Üniversitesi', 'agri.edu.tr'),
  ('Aksaray Üniversitesi', 'aksaray.edu.tr'),
  ('Amasya Üniversitesi', 'amasya.edu.tr'),
  ('Jandarma ve Sahil Güvenlik Akademisi', 'jsg.edu.tr'),
  ('Ankara Üniversitesi', 'ankara.edu.tr'),
  ('Ankara Müzik ve Güzel Sanatlar Üniversitesi', 'mgu.edu.tr'),
  ('Ankara Hacı Bayram Veli Üniversitesi', 'hbv.edu.tr'),
  ('Ankara Sosyal Bilimler Üniversitesi', 'asbu.edu.tr'),
  ('Gazi Üniversitesi', 'gazi.edu.tr'),
  ('Hacettepe Üniversitesi', 'hacettepe.edu.tr'),
  ('Orta Doğu Teknik Üniversitesi', 'metu.edu.tr'),
  ('Ankara Yıldırım Beyazıt Üniversitesi', 'aybu.edu.tr'),
  ('Polis Akademisi', 'pa.edu.tr'),
  ('Akdeniz Üniversitesi', 'akdeniz.edu.tr'),
  ('Alanya Alaaddin Keykubat Üniversitesi', 'alku.edu.tr'),
  ('Ardahan Üniversitesi', 'ardahan.edu.tr'),
  ('Artvin Çoruh Üniversitesi', 'artvin.edu.tr'),
  ('Aydın Adnan Menderes Üniversitesi', 'adu.edu.tr'),
  ('Balıkesir Üniversitesi', 'balikesir.edu.tr'),
  ('Bandırma Onyedi Eylül Üniversitesi', 'bandirma.edu.tr'),
  ('Bartın Üniversitesi', 'bartin.edu.tr'),
  ('Batman Üniversitesi', 'batman.edu.tr'),
  ('Bayburt Üniversitesi', 'bayburt.edu.tr'),
  ('Bilecik Şeyh Edebali Üniversitesi', 'bilecik.edu.tr'),
  ('Bingöl Üniversitesi', 'bingol.edu.tr'),
  ('Bitlis Eren Üniversitesi', 'beu.edu.tr'),
  ('Bolu Abant İzzet Baysal Üniversitesi', 'ibu.edu.tr'),
  ('Burdur Mehmet Akif Ersoy Üniversitesi', 'mehmetakif.edu.tr'),
  ('Bursa Teknik Üniversitesi', 'btu.edu.tr'),
  ('Bursa Uludağ Üniversitesi', 'uludag.edu.tr'),
  ('Çanakkale Onsekiz Mart Üniversitesi', 'comu.edu.tr'),
  ('Çankırı Karatekin Üniversitesi', 'karatekin.edu.tr'),
  ('Hitit Üniversitesi', 'hitit.edu.tr'),
  ('Pamukkale Üniversitesi', 'pau.edu.tr'),
  ('Dicle Üniversitesi', 'dicle.edu.tr'),
  ('Düzce Üniversitesi', 'duzce.edu.tr'),
  ('Trakya Üniversitesi', 'trakya.edu.tr'),
  ('Fırat Üniversitesi', 'firat.edu.tr'),
  ('Erzincan Binali Yıldırım Üniversitesi', 'ebyu.edu.tr'),
  ('Atatürk Üniversitesi', 'atauni.edu.tr'),
  ('Erzurum Teknik Üniversitesi', 'erzurum.edu.tr'),
  ('Anadolu Üniversitesi', 'anadolu.edu.tr'),
  ('Eskişehir Osmangazi Üniversitesi', 'ogu.edu.tr'),
  ('Eskişehir Teknik Üniversitesi', 'eskisehir.edu.tr'),
  ('Gaziantep Üniversitesi', 'gaziantep.edu.tr'),
  ('Gaziantep İslam Bilim ve Teknoloji Üniversitesi', 'gibtu.edu.tr'),
  ('Giresun Üniversitesi', 'giresun.edu.tr'),
  ('Gümüşhane Üniversitesi', 'gumushane.edu.tr'),
  ('Hakkari Üniversitesi', 'hakkari.edu.tr'),
  ('İskenderun Teknik Üniversitesi', 'iste.edu.tr'),
  ('Hatay Mustafa Kemal Üniversitesi', 'mku.edu.tr'),
  ('Iğdır Üniversitesi', 'igdir.edu.tr'),
  ('Süleyman Demirel Üniversitesi', 'sdu.edu.tr'),
  ('Isparta Uygulamalı Bilimler Üniversitesi', 'isparta.edu.tr'),
  ('Boğaziçi Üniversitesi', 'boun.edu.tr'),
  ('Galatasaray Üniversitesi', 'gsu.edu.tr'),
  ('İstanbul Medeniyet Üniversitesi', 'medeniyet.edu.tr'),
  ('İstanbul Teknik Üniversitesi', 'itu.edu.tr'),
  ('İstanbul Üniversitesi', 'istanbul.edu.tr'),
  ('İstanbul Üniversitesi-Cerrahpaşa', 'iuc.edu.tr'),
  ('Marmara Üniversitesi', 'marmara.edu.tr'),
  ('Milli Savunma Üniversitesi', 'msu.edu.tr'),
  ('Mimar Sinan Güzel Sanatlar Üniversitesi', 'msgsu.edu.tr'),
  ('Türk-Alman Üniversitesi', 'tau.edu.tr'),
  ('Türk-Japon Bilim ve Teknoloji Üniversitesi', 'tju.edu.tr'),
  ('Sağlık Bilimleri Üniversitesi', 'sbu.edu.tr'),
  ('Yıldız Teknik Üniversitesi', 'yildiz.edu.tr'),
  ('Dokuz Eylül Üniversitesi', 'deu.edu.tr'),
  ('Ege Üniversitesi', 'ege.edu.tr'),
  ('İzmir Yüksek Teknoloji Enstitüsü', 'iyte.edu.tr'),
  ('İzmir Kâtip Çelebi Üniversitesi', 'ikcu.edu.tr'),
  ('İzmir Bakırçay Üniversitesi', 'bakircay.edu.tr'),
  ('İzmir Demokrasi Üniversitesi', 'idu.edu.tr'),
  ('Kahramanmaraş Sütçü İmam Üniversitesi', 'ksu.edu.tr'),
  ('Kahramanmaraş İstiklal Üniversitesi', 'istiklal.edu.tr'),
  ('Karabük Üniversitesi', 'karabuk.edu.tr'),
  ('Karamanoğlu Mehmetbey Üniversitesi', 'kmu.edu.tr'),
  ('Kafkas Üniversitesi', 'kafkas.edu.tr'),
  ('Kastamonu Üniversitesi', 'kastamonu.edu.tr'),
  ('Abdullah Gül Üniversitesi', 'agu.edu.tr'),
  ('Erciyes Üniversitesi', 'erciyes.edu.tr'),
  ('Kayseri Üniversitesi', 'kayseri.edu.tr'),
  ('Kırıkkale Üniversitesi', 'kku.edu.tr'),
  ('Kırklareli Üniversitesi', 'klu.edu.tr'),
  ('Kırşehir Ahi Evran Üniversitesi', 'ahievran.edu.tr'),
  ('Kilis 7 Aralık Üniversitesi', 'kilis.edu.tr'),
  ('Gebze Teknik Üniversitesi', 'gtu.edu.tr'),
  ('Kocaeli Üniversitesi', 'kocaeli.edu.tr'),
  ('Konya Teknik Üniversitesi', 'ktun.edu.tr'),
  ('Necmettin Erbakan Üniversitesi', 'erbakan.edu.tr'),
  ('Selçuk Üniversitesi', 'selcuk.edu.tr'),
  ('Kütahya Dumlupınar Üniversitesi', 'dpu.edu.tr'),
  ('Kütahya Sağlık Bilimleri Üniversitesi', 'ksb.edu.tr'),
  ('İnönü Üniversitesi', 'inonu.edu.tr'),
  ('Malatya Turgut Özal Üniversitesi', 'ozal.edu.tr'),
  ('Manisa Celal Bayar Üniversitesi', 'mcbu.edu.tr'),
  ('Mardin Artuklu Üniversitesi', 'artuklu.edu.tr'),
  ('Mersin Üniversitesi', 'mersin.edu.tr'),
  ('Tarsus Üniversitesi', 'tarsus.edu.tr'),
  ('Muğla Sıtkı Koçman Üniversitesi', 'mu.edu.tr'),
  ('Muş Alparslan Üniversitesi', 'alparslan.edu.tr'),
  ('Nevşehir Hacı Bektaş Veli Üniversitesi', 'nevsehir.edu.tr'),
  ('Niğde Ömer Halisdemir Üniversitesi', 'ohu.edu.tr'),
  ('Ordu Üniversitesi', 'odu.edu.tr'),
  ('Osmaniye Korkut Ata Üniversitesi', 'osmaniye.edu.tr'),
  ('Recep Tayyip Erdoğan Üniversitesi', 'erdogan.edu.tr'),
  ('Sakarya Üniversitesi', 'sakarya.edu.tr'),
  ('Sakarya Uygulamalı Bilimler Üniversitesi', 'subu.edu.tr'),
  ('Ondokuz Mayıs Üniversitesi', 'omu.edu.tr'),
  ('Samsun Üniversitesi', 'samsun.edu.tr'),
  ('Siirt Üniversitesi', 'siirt.edu.tr'),
  ('Sinop Üniversitesi', 'sinop.edu.tr'),
  ('Sivas Cumhuriyet Üniversitesi', 'cumhuriyet.edu.tr'),
  ('Sivas Bilim ve Teknoloji Üniversitesi', 'sbtu.edu.tr'),
  ('Harran Üniversitesi', 'harran.edu.tr'),
  ('Şırnak Üniversitesi', 'sirnak.edu.tr'),
  ('Tekirdağ Namık Kemal Üniversitesi', 'nku.edu.tr'),
  ('Tokat Gaziosmanpaşa Üniversitesi', 'gop.edu.tr'),
  ('Karadeniz Teknik Üniversitesi', 'ktu.edu.tr'),
  ('Trabzon Üniversitesi', 'trabzon.edu.tr'),
  ('Munzur Üniversitesi', 'munzur.edu.tr'),
  ('Uşak Üniversitesi', 'usak.edu.tr'),
  ('Van Yüzüncü Yıl Üniversitesi', 'yyu.edu.tr'),
  ('Yalova Üniversitesi', 'yalova.edu.tr'),
  ('Yozgat Bozok Üniversitesi', 'bozok.edu.tr'),
  ('Zonguldak Bülent Ecevit Üniversitesi', 'beun.edu.tr'),
  ('Ankara Bilim Üniversitesi', 'ankarabilim.edu.tr'),
  ('Ankara Medipol Üniversitesi', 'ankaramedipol.edu.tr'),
  ('Atılım Üniversitesi', 'atilim.edu.tr'),
  ('Başkent Üniversitesi', 'baskent.edu.tr'),
  ('Çankaya Üniversitesi', 'cankaya.edu.tr'),
  ('İhsan Doğramacı Bilkent Üniversitesi', 'bilkent.edu.tr'),
  ('Lokman Hekim Üniversitesi', 'lokmanhekim.edu.tr'),
  ('Ostim Teknik Üniversitesi', 'ostimteknik.edu.tr'),
  ('TED Üniversitesi', 'tedu.edu.tr'),
  ('TOBB Ekonomi ve Teknoloji Üniversitesi', 'etu.edu.tr'),
  ('Ufuk Üniversitesi', 'ufuk.edu.tr'),
  ('Türk Hava Kurumu Üniversitesi', 'thk.edu.tr'),
  ('Yüksek İhtisas Üniversitesi', 'yuksekihtisas.edu.tr'),
  ('Alanya Üniversitesi', 'alanya.edu.tr'),
  ('Antalya Belek Üniversitesi', 'belek.edu.tr'),
  ('Antalya Bilim Üniversitesi', 'antalyabilim.edu.tr'),
  ('Mudanya Üniversitesi', 'mudanya.edu.tr'),
  ('Hasan Kalyoncu Üniversitesi', 'hku.edu.tr'),
  ('Sanko Üniversitesi', 'sanko.edu.tr'),
  ('Acıbadem Üniversitesi', 'acibadem.edu.tr'),
  ('Altınbaş Üniversitesi', 'altinbas.edu.tr'),
  ('Bahçeşehir Üniversitesi', 'bahcesehir.edu.tr'),
  ('Beykoz Üniversitesi', 'beykoz.edu.tr'),
  ('Bezmialem Vakıf Üniversitesi', 'bezmialem.edu.tr'),
  ('Biruni Üniversitesi', 'biruni.edu.tr'),
  ('Demiroğlu Bilim Üniversitesi', 'demiroglu.bilim.edu.tr'),
  ('Doğuş Üniversitesi', 'dogus.edu.tr'),
  ('Fatih Sultan Mehmet Üniversitesi', 'fsm.edu.tr'),
  ('Fenerbahçe Üniversitesi', 'fbu.edu.tr'),
  ('Haliç Üniversitesi', 'halic.edu.tr'),
  ('Işık Üniversitesi', 'isikun.edu.tr'),
  ('İbn Haldun Üniversitesi', 'ibnhaldun.edu.tr'),
  ('İstanbul 29 Mayıs Üniversitesi', '29mayis.edu.tr'),
  ('İstanbul Arel Üniversitesi', 'arel.edu.tr'),
  ('İstanbul Atlas Üniversitesi', 'atlas.edu.tr'),
  ('İstanbul Aydın Üniversitesi', 'aydin.edu.tr'),
  ('İstanbul Beykent Üniversitesi', 'beykent.edu.tr'),
  ('İstanbul Bilgi Üniversitesi', 'bilgi.edu.tr'),
  ('İstanbul Esenyurt Üniversitesi', 'esenyurt.edu.tr'),
  ('İstanbul Galata Üniversitesi', 'galata.edu.tr'),
  ('İstanbul Gedik Üniversitesi', 'gedik.edu.tr'),
  ('İstanbul Gelişim Üniversitesi', 'gelisim.edu.tr'),
  ('İstanbul Kent Üniversitesi', 'kent.edu.tr'),
  ('İstanbul Kültür Üniversitesi', 'iku.edu.tr'),
  ('İstanbul Medipol Üniversitesi', 'medipol.edu.tr'),
  ('İstanbul Nişantaşı Üniversitesi', 'nisantasi.edu.tr'),
  ('İstanbul Okan Üniversitesi', 'okan.edu.tr'),
  ('İstanbul Rumeli Üniversitesi', 'rumeli.edu.tr'),
  ('İstanbul Sabahattin Zaim Üniversitesi', 'izu.edu.tr'),
  ('İstanbul Sağlık ve Teknoloji Üniversitesi', 'istun.edu.tr'),
  ('İstanbul Ticaret Üniversitesi', 'ticaret.edu.tr'),
  ('İstanbul Topkapı Üniversitesi', 'topkapi.edu.tr'),
  ('İstanbul Yeni Yüzyıl Üniversitesi', 'yeniyuzyil.edu.tr'),
  ('İstinye Üniversitesi', 'istinye.edu.tr'),
  ('Kadir Has Üniversitesi', 'khas.edu.tr'),
  ('Koç Üniversitesi', 'ku.edu.tr'),
  ('Maltepe Üniversitesi', 'maltepe.edu.tr'),
  ('MEF Üniversitesi', 'mef.edu.tr'),
  ('Özyeğin Üniversitesi', 'ozyegin.edu.tr'),
  ('Piri Reis Üniversitesi', 'piriuint.edu.tr'),
  ('Sabancı Üniversitesi', 'sabanciuniv.edu'),
  ('Üsküdar Üniversitesi', 'uskudar.edu.tr'),
  ('Yeditepe Üniversitesi', 'yeditepe.edu.tr'),
  ('İzmir Ekonomi Üniversitesi', 'ieu.edu.tr'),
  ('İzmir Tınaztepe Üniversitesi', 'tinaztepe.edu.tr'),
  ('Yaşar Üniversitesi', 'yasar.edu.tr'),
  ('Nuh Naci Yazgan Üniversitesi', 'nny.edu.tr'),
  ('Kocaeli Sağlık ve Teknoloji Üniversitesi', 'kstu.edu.tr'),
  ('Konya Gıda ve Tarım Üniversitesi', 'gidatarim.edu.tr'),
  ('KTO Karatay Üniversitesi', 'karatay.edu.tr'),
  ('Çağ Üniversitesi', 'cag.edu.tr'),
  ('Toros Üniversitesi', 'toros.edu.tr'),
  ('Kapadokya Üniversitesi', 'kapadokya.edu.tr'),
  ('Avrasya Üniversitesi', 'avrasya.edu.tr'),
  ('İstanbul Sağlık ve Sosyal Bilimler Meslek Yüksekokulu', 'ism.edu.tr'),
  ('Ataşehir Adıgüzel Meslek Yüksekokulu', 'adiguzel.edu.tr'),
  ('İstanbul Şişli Meslek Yüksekokulu', 'sisli.edu.tr'),
  ('İzmir Kavram Meslek Yüksekokulu', 'kavram.edu.tr');

INSERT INTO users (name, username, email, password_hash, photo_url, latitude, longitude, role, university_id)
VALUES
  ('Onat Budak', 'onat', 'onat@itu.edu.tr', '$2b$12$Fq1S.8b9.d8z.R.t.k.D.e.M.I.w.I.c.j.e.S.b.C.j.F.w.q', NULL, 41.1050, 29.0250, 'USER', 64),
  ('Ada Lovelace', 'ada', 'ada@boun.edu.tr', '$2b$12$Fq1S.8b9.d8z.R.t.k.D.e.M.I.w.I.c.j.e.S.b.C.j.F.w.q', NULL, 41.0853, 29.0434, 'ADMIN', 61),
  ('Grace Hopper', 'grace', 'grace@metu.edu.tr', '$2b$12$Fq1S.8b9.d8z.R.t.k.D.e.M.I.w.I.c.j.e.S.b.C.j.F.w.q', NULL, 39.9334, 32.8597, 'USER', 16),
  ('Alan Turing', 'alant', 'turing@gazi.edu.tr', '$2b$12$Fq1S.8b9.d8z.R.t.k.D.e.M.I.w.I.c.j.e.S.b.C.j.F.w.q', NULL, 51.5074, -0.1278, 'USER', 14),
  ('Linus Torvalds', 'linus', 'linus@sabanciuniv.edu', '$2b$12$Fq1S.8b9.d8z.R.t.k.D.e.M.I.w.I.c.j.e.S.b.C.j.F.w.q', NULL, 60.1699, 24.9384, 'USER', 200),
  ('Elon Musk', 'elon', 'elon@ku.edu.tr', '$2b$12$Fq1S.8b9.d8z.R.t.k.D.e.M.I.w.I.c.j.e.S.b.C.j.F.w.q', NULL, 34.0522, -118.2437, 'USER', 196),
  ('Mark Zuckerberg', 'markz', 'mark@yildiz.edu.tr', '$2b$12$Fq1S.8b9.d8z.R.t.k.D.e.M.I.w.I.c.j.e.S.b.C.j.F.w.q', NULL, 37.4848, -122.1484, 'USER', 74);


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