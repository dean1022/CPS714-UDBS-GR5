-- Exported from merged SQLite library.db, preserving Megan account password hashes.
-- Run only on a fresh schema; repeat execution uses ON CONFLICT DO NOTHING.
BEGIN;
INSERT INTO "category" ("category_id","name") VALUES (1,'Computer Science') ON CONFLICT DO NOTHING;
INSERT INTO "category" ("category_id","name") VALUES (3,'Software Engineering') ON CONFLICT DO NOTHING;
INSERT INTO "category" ("category_id","name") VALUES (4,'Physics') ON CONFLICT DO NOTHING;
INSERT INTO "category" ("category_id","name") VALUES (5,'History') ON CONFLICT DO NOTHING;
INSERT INTO "author" ("author_id","name") VALUES (1,'Abraham Silberschatz') ON CONFLICT DO NOTHING;
INSERT INTO "author" ("author_id","name") VALUES (2,'Thomas Cormen') ON CONFLICT DO NOTHING;
INSERT INTO "author" ("author_id","name") VALUES (3,'Robert Martin') ON CONFLICT DO NOTHING;
INSERT INTO "author" ("author_id","name") VALUES (4,'Stephen Hawking') ON CONFLICT DO NOTHING;
INSERT INTO "author" ("author_id","name") VALUES (5,'Yuval Harari') ON CONFLICT DO NOTHING;
INSERT INTO "keyword" ("keyword_id","word") VALUES (1,'databases') ON CONFLICT DO NOTHING;
INSERT INTO "keyword" ("keyword_id","word") VALUES (2,'sql') ON CONFLICT DO NOTHING;
INSERT INTO "keyword" ("keyword_id","word") VALUES (3,'algorithms') ON CONFLICT DO NOTHING;
INSERT INTO "keyword" ("keyword_id","word") VALUES (4,'programming') ON CONFLICT DO NOTHING;
INSERT INTO "keyword" ("keyword_id","word") VALUES (5,'space') ON CONFLICT DO NOTHING;
INSERT INTO "keyword" ("keyword_id","word") VALUES (6,'black holes') ON CONFLICT DO NOTHING;
INSERT INTO "keyword" ("keyword_id","word") VALUES (7,'humans') ON CONFLICT DO NOTHING;
INSERT INTO "keyword" ("keyword_id","word") VALUES (8,'evolution') ON CONFLICT DO NOTHING;
INSERT INTO "literature" ("literature_id","category_id","title","publication_year","file_url","total_access_slots","loan_period_days") VALUES (1,1,'Database System Concepts',2019,'database-system-concepts.txt',15,14) ON CONFLICT DO NOTHING;
INSERT INTO "literature" ("literature_id","category_id","title","publication_year","file_url","total_access_slots","loan_period_days") VALUES (2,1,'Introduction to Algorithms',2022,'introduction-to-algorithms.txt',15,14) ON CONFLICT DO NOTHING;
INSERT INTO "literature" ("literature_id","category_id","title","publication_year","file_url","total_access_slots","loan_period_days") VALUES (3,3,'Clean Code',2008,'clean-code.txt',15,14) ON CONFLICT DO NOTHING;
INSERT INTO "literature" ("literature_id","category_id","title","publication_year","file_url","total_access_slots","loan_period_days") VALUES (4,4,'A Brief History of Time',1998,'a-brief-history-of-time.txt',15,14) ON CONFLICT DO NOTHING;
INSERT INTO "literature" ("literature_id","category_id","title","publication_year","file_url","total_access_slots","loan_period_days") VALUES (5,5,'Sapiens',2015,'sapiens.txt',15,14) ON CONFLICT DO NOTHING;
INSERT INTO "literature_author" ("literature_id","author_id") VALUES (1,1) ON CONFLICT DO NOTHING;
INSERT INTO "literature_author" ("literature_id","author_id") VALUES (2,2) ON CONFLICT DO NOTHING;
INSERT INTO "literature_author" ("literature_id","author_id") VALUES (3,3) ON CONFLICT DO NOTHING;
INSERT INTO "literature_author" ("literature_id","author_id") VALUES (4,4) ON CONFLICT DO NOTHING;
INSERT INTO "literature_author" ("literature_id","author_id") VALUES (5,5) ON CONFLICT DO NOTHING;
INSERT INTO "literature_keyword" ("literature_id","keyword_id") VALUES (1,1) ON CONFLICT DO NOTHING;
INSERT INTO "literature_keyword" ("literature_id","keyword_id") VALUES (1,2) ON CONFLICT DO NOTHING;
INSERT INTO "literature_keyword" ("literature_id","keyword_id") VALUES (2,3) ON CONFLICT DO NOTHING;
INSERT INTO "literature_keyword" ("literature_id","keyword_id") VALUES (3,4) ON CONFLICT DO NOTHING;
INSERT INTO "literature_keyword" ("literature_id","keyword_id") VALUES (4,5) ON CONFLICT DO NOTHING;
INSERT INTO "literature_keyword" ("literature_id","keyword_id") VALUES (4,6) ON CONFLICT DO NOTHING;
INSERT INTO "literature_keyword" ("literature_id","keyword_id") VALUES (5,7) ON CONFLICT DO NOTHING;
INSERT INTO "literature_keyword" ("literature_id","keyword_id") VALUES (5,8) ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('501000001','ava.chen@torontomu.ca','3e25e8848bbebb1c$20b71dd7fe31c87b902237875ef360081efd3d70f3a057efb7f631f898acedca','Ava','Chen','Ava','she/they','student') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('501000002','liam.singh@torontomu.ca','6146ca294b13d9da$22e292f065293c350ea52d8cd7c6f8720b1e6705e117da55314ff6007d9b4810','Liam','Singh','Liam','he/him','student') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('501000003','noor.haddad@torontomu.ca','fc62eaf1fdd662e4$15eeb880a161cfc53616ee8b8cef66f1447513f15e9f700605d3085b9607db46','Noor','Haddad','Noor','she/her','student') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('501000004','ethan.tremblay@torontomu.ca','55c6b5f50e554f4d$6f3e8599841534b09b489d8feabe27e8ef41acc8f40861a3f702c3430991b79b','Ethan','Tremblay','Ethan','he/him','student') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('501000005','alex.ferreira@torontomu.ca','41676dfad30541a6$7b8e1f6630c01917779fc44b4c4d165d7d68e533ed2a92eb585b1dacccaf80c8','Alex','Ferreira','Alex','they/them','student') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('501000006','jordan.reyes@torontomu.ca','6692e90d28dbbe04$731259de010b48435a6db5cd0f911ddab97e14432b1b0e40ab99d5d2fce73433','Jordan','Reyes','Jordan','they/them','student') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('501000007','priya.patel@torontomu.ca','2436829968c1694a$c81b66f96704dcb497881d02fb3430df25677fc9b552c58ee771cbf1a3e85eaa','Priya','Patel','Priya','she/her','student') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('501000008','lucas.moreau@torontomu.ca','d2fc2b4b42a592a8$ee6a49f0dd35a4994491b3f3d5e5549611b8aaeb32456912090d1ff61e40bd1a','Lucas','Moreau','Lucas','he/they','student') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('501000009','sofia.rossi@torontomu.ca','c3571556662996aa$4e4fbb3c2297672a46bd6a511a1a932554caa0d3b36f862cdd3f30a8e1a808d0','Sofia','Rossi','Sofia','she/her','student') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('501000010','daniel.kim@torontomu.ca','ebd888d328cf4419$efb265f4b1f1899af888c28161324d1d02688295b4d1ecb14aa8c1acc43844ff','Daniel','Kim','Daniel','he/him','student') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('700000001','elaine.whitfield@torontomu.ca','09e405ddee3c2474$8d14931cec77d12022ba5bb4dde0c898620ff89ca526e772e89bf488c59a6225','Elaine','Whitfield','Elaine','she/her','faculty') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('700000002','marcus.adeyemi@torontomu.ca','074873e0e1895307$9f090f0873d6a7c6f1bcffb50698fa5db483cd7cdb4324e2b66f4843683bd92d','Marcus','Adeyemi','Marcus','he/him','faculty') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('700000003','hana.yamamoto@torontomu.ca','97605e459d6035a8$56d157fc5151d4e5cf7e85e825089dc60376e4e9193341c3b96abe7860cfc86e','Hana','Yamamoto','Hana','she/her','faculty') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('700000004','robert.gallagher@torontomu.ca','bdca7a3966f39380$78a45dd882b117d255a8e008cf4e5ec26a1bf29541e3d378bc4cb6c80e0754b1','Robert','Gallagher','Robert','he/him','faculty') ON CONFLICT DO NOTHING;
INSERT INTO "users" ("university_id","email","password_hash","first_name","last_name","display_name","pronouns","status") VALUES ('700000005','fatima.rahman@torontomu.ca','42d255b0822c5d31$21185ddbdad70bc2e18b4d05500def270d330cf6a21903cb238558be5e3047b3','Fatima','Rahman','Fatima','she/her','faculty') ON CONFLICT DO NOTHING;
UPDATE "library_user" SET max_loans=30, max_holds=15;
UPDATE literature SET total_access_slots=15, loan_period_days=14;
SELECT setval(pg_get_serial_sequence('"library_user"','user_id'),COALESCE((SELECT MAX(user_id) FROM "library_user"),1),true);
SELECT setval(pg_get_serial_sequence('"category"','category_id'),COALESCE((SELECT MAX(category_id) FROM "category"),1),true);
SELECT setval(pg_get_serial_sequence('"author"','author_id'),COALESCE((SELECT MAX(author_id) FROM "author"),1),true);
SELECT setval(pg_get_serial_sequence('"keyword"','keyword_id'),COALESCE((SELECT MAX(keyword_id) FROM "keyword"),1),true);
SELECT setval(pg_get_serial_sequence('"literature"','literature_id'),COALESCE((SELECT MAX(literature_id) FROM "literature"),1),true);
UPDATE literature SET summary='The text is designed for a first course in databases at the junior/senior undergraduate level or the first year graduate level. It also contains additional material that can be used as supplements or as introductory material for an advanced course. Because the authors present concepts as intuitive descriptions, a familiarity with basic data structures, computer organization, and a high-level programming language are the only prerequisites. Important theoretical results are covered, but formal proofs are omitted. In place of proofs, figures and examples are used to suggest why a result is true.' WHERE literature_id=1;
UPDATE literature SET summary='A comprehensive update of the leading algorithms text, with new material on matchings in bipartite graphs, online algorithms, machine learning, and other topics.

Some books on algorithms are rigorous but incomplete; others cover masses of material but lack rigor. Introduction to Algorithms uniquely combines rigor and comprehensiveness. It covers a broad range of algorithms in depth, yet makes their design and analysis accessible to all levels of readers, with self-contained chapters and algorithms in pseudocode. Since the publication of the first edition, Introduction to Algorithms has become the leading algorithms text in universities worldwide as well as the standard reference for professionals. This fourth edition has been updated throughout.' WHERE literature_id=2;
UPDATE literature SET summary='Even bad code can function. But if code isn’t clean, it can bring a development organization to its knees. Every year, countless hours and significant resources are lost because of poorly written code. But it doesn’t have to be that way.

Noted software expert Robert C. Martin presents a revolutionary paradigm with Clean Code: A Handbook of Agile Software Craftsmanship. Martin has teamed up with his colleagues from Object Mentor to distill their best agile practice of cleaning code “on the fly” into a book that will instill within you the values of a software craftsman and make you a better programmer—but only if you work at it.

What kind of work will you be doing? You’ll be reading code—lots of code. And you will be challenged to think about what’s right about that code, and what’s wrong with it. More importantly, you will be challenged to reassess your professional values and your commitment to your craft.

Clean Code is divided into three parts. The first describes the principles, patterns, and practices of writing clean code. The second part consists of several case studies of increasing complexity. Each case study is an exercise in cleaning up code—of transforming a code base that has some problems into one that is sound and efficient. The third part is the payoff: a single chapter containing a list of heuristics and “smells” gathered while creating the case studies. The result is a knowledge base that describes the way we think when we write, read, and clean code.' WHERE literature_id=3;
UPDATE literature SET summary='A landmark volume in science writing by one of the great minds of our time, Stephen Hawking’s book explores such profound questions as: How did the universe begin—and what made its start possible? Does time always flow forward? Is the universe unending—or are there boundaries? Are there other dimensions in space? What will happen when it all ends?

Told in language we all can understand, A Brief History of Time plunges into the exotic realms of black holes and quarks, of antimatter and “arrows of time,” of the big bang and a bigger God—where the possibilities are wondrous and unexpected. With exciting images and profound imagination, Stephen Hawking brings us closer to the ultimate secrets at the very heart of creation.' WHERE literature_id=4;
UPDATE literature SET summary='Volume one of the epic, beautifully illustrated graphic history of humankind, based on Yuval Noah Harari''s internationally bestselling phenomenon

In a world deluged by irrelevant information, clarity is power. How can we see the big picture without getting caught up in an infinity of little details? One way is to step back, to look at the really big picture: the entire history of the human species. Sapiens: A Graphic History, The Birth of Humankind is the story of how an insignificant ape became the ruler of planet Earth, capable of splitting the atom, flying to the Moon, and manipulating the genetic code of life.

With Yuval Noah Harari as your guide, and accompanied by characters like Prehistoric Bill, Dr. Fiction, and Detective Lopez, you are invited to take a ride on the wild side of history. The graphic format offers readers a new intellectual and artistic exploration of the past. Human evolution is reimagined as a tacky reality TV show. The first encounter between Sapiens and Neanderthals is explored through the masterpieces of modern art. The extinction of the mammoths and saber-toothed tigers is retold as a "whodunit" movie. Sapiens: A Graphic History is a radical, and radically fun, retelling of the story of humankind, bursting with wit, humor, and colorful characters. If you want to know why we are all trapped inside the dreams of dead people — read this book.' WHERE literature_id=5;
COMMIT;
