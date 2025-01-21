SELECT * FROM people, study, login, publicMessages, comments, privateMessages, category
WHERE people.id = login.personid AND (people.id = privateMessages.senderid OR people.id = privateMessages.recipientid) 
AND people.id = comments.senderid AND publicMessages.senderid = people.id AND people.studyid = study.id
AND comments.messageid = publicMessages.id AND publicMessages.categoryid = category.id;

INSERT INTO category(name)
VALUES ('Dansk'),
       ('Engelsk'),
       ('Andet sprog'),
       ('Matematik'),
       ('Fysik'),
       ('Kemi'),
       ('Biologi'),
       ('Historie'),
       ('Samfundsfag'),
       ('Religion'),
       ('Geografi'),
       ('Idræt'),
       ('Programmering'),
       ('Design'),
       ('Psykologi'),
       ('Erhvervsøkonomi'),
       ('Innovation'),
       ('Teknologi'),
       ('Kommunikation og IT'),
       ('Informatik'),
       ('Medicin'),
       ('Økonomi'),
       ('Andet');