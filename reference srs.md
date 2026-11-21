`DEPARTMENT OF COMPUTER SCIENCE[span_0](start_span)[span_0](end_span)`  
`ALIGARH MUSLIM UNIVERSITY, ALIGARH-202002[span_1](start_span)[span_1](end_span)`

`M.C.A SEMESTER - III[span_2](start_span)[span_2](end_span)`  
`SESSION: 2025-26[span_3](start_span)[span_3](end_span)`  
`CAMS-3P01: MINI PROJECT[span_4](start_span)[span_4](end_span)`

`PLACEMENTCONNECT (PLACEMENT MANAGEMENT SYSTEM)[span_5](start_span)[span_5](end_span)`  
`SOFTWARE REQUIREMENT SPECIFICATION[span_6](start_span)[span_6](end_span)`

`SUBMITTED BY -[span_7](start_span)[span_7](end_span)`  
`NAME: MOHD RAMEEZ KHAN[span_8](start_span)[span_8](end_span)`  
`FACULTY No: 24CAMSA124[span_9](start_span)[span_9](end_span)`  
`ENROLLMENT NO: GL5698[span_10](start_span)[span_10](end_span)`

`SUBMITTED TO -[span_11](start_span)[span_11](end_span)`  
`MS. SAJIDA KHATOON[span_12](start_span)[span_12](end_span)`

`================================================================================`  
`TABLE OF CONTENTS`  
`================================================================================`  
`1. Information Gathering Methods............................................... 1[span_13](start_span)[span_13](end_span)`  
   `1.1 Method Comparison....................................................... 1[span_14](start_span)[span_14](end_span)`  
`2. Detailed Requirements Specification......................................... 3[span_15](start_span)[span_15](end_span)`  
   `2.1 Functional Requirements................................................. 3[span_16](start_span)[span_16](end_span)`  
   `2.2 Non-Functional Requirements............................................. 4[span_17](start_span)[span_17](end_span)`  
   `2.3 Data Requirements....................................................... 5[span_18](start_span)[span_18](end_span)`  
   `2.4 System Requirements..................................................... 6[span_19](start_span)[span_19](end_span)`  
`3. Design and Analysis......................................................... 8[span_20](start_span)[span_20](end_span)`  
   `3.1 System Architecture..................................................... 8[span_21](start_span)[span_21](end_span)`  
   `3.2 Detailed Design Diagram................................................ 13[span_22](start_span)[span_22](end_span)`  
   `3.3 Design Tools and Limitations........................................... 26[span_23](start_span)[span_23](end_span)`  
`4. Implementation............................................................. 27[span_24](start_span)[span_24](end_span)`  
   `4.1 Technology Stack Justification......................................... 27[span_25](start_span)[span_25](end_span)`  
   `4.2 Interface Design....................................................... 27[span_26](start_span)[span_26](end_span)`  
   `4.3 Implementation Status.................................................. 28[span_27](start_span)[span_27](end_span)`

`================================================================================`  
`1. INFORMATION GATHERING METHODS[span_28](start_span)[span_28](end_span)`  
`================================================================================`

`1.1 Method Comparison[span_29](start_span)[span_29](end_span)`

`Method 1: Academic Literature Review[span_30](start_span)[span_30](end_span)`  
`• Strengths: This method provides a comprehensive, peer-reviewed, and theoretical`  
  `foundation for the project. It helps in understanding established principles and the`  
  `shortcomings of existing systems documented in academic papers.[span_31](start_span)[span_31](end_span)`  
`• Weaknesses: Academic literature can sometimes be outdated and may lack practical, real-`  
  `world implementation examples with modern technology stacks.[span_32](start_span)[span_32](end_span)`  
`• Application: We analyzed three literature reviews in the "Existing Works" section of the`  
  `synopsis. This allowed us to identify gaps in their functionality, such as a lack of real-time`  
  `notifications and seamless CI/CD pipelines, which PlacementConnect aims to address.[span_33](start_span)[span_33](end_span)`

`Method 2: Superset (Industry Case Study)[span_34](start_span)[span_34](end_span)`  
`• Strengths: Superset has been successfully adopted by over 600 college placement cells,`  
  `demonstrating its ability to handle real-world, large-scale operations. It offers a conflict-`  
  `free calendar system, drag-and-drop rescheduling, bulk reminders, recruiter dashboards,`  
  `offer uploads, and live analytics for placement drives. Its proven multi-campus and`  
  `multilingual deployment highlight its reliability and adaptability across varied institutional`  
  `contexts.[span_35](start_span)[span_35](end_span)`  
`• Weaknesses: While public information emphasizes its operational benefits, there is little`  
  `detail on its underlying extensibility, database schema control, or support for rapid CI/CD`  
  `workflows. Because Superset follows a hosted, standardized model, campus-specific`  
  `customizations may depend on the vendor's development timeline rather than the`  
  `institution's own pace.[span_36](start_span)[span_36](end_span)`  
`• Application: We used Superset's placement system as an example while designing our`  
  `system. Its features like checking for schedule clashes, sending automatic reminders,`  
  `letting recruiters manage their own tasks, and keeping job offer details updated-helped`  
  `us understand what we need to handle busy placement periods and keep everyone working`  
  `together easily.[span_37](start_span)[span_37](end_span)[span_38](start_span)[span_38](end_span)`

`Most Effective Approach:[span_39](start_span)[span_39](end_span)`  
`A combination of both methods was the most effective approach. The academic literature review`  
`provided the foundational problem statement and justification, while the analysis of Superset in`  
`industry case study helped in defining the specific features and technological advantages that`  
`would make PlacementConnect a superior and more modern solution.[span_40](start_span)[span_40](end_span)`

`================================================================================`  
`2. DETAILED REQUIREMENTS SPECIFICATION[span_41](start_span)[span_41](end_span)`  
`================================================================================`

`2.1 Functional Requirements[span_42](start_span)[span_42](end_span)`

`FR-001: User Account Registration[span_43](start_span)[span_43](end_span)`  
`• Description: The system shall provide secure login and registration for Students,`  
  `TPO Administrators, and Company Recruiters with role-based access control. New`  
  `users must select their role (Student, TPO Administrator, or Company Recruiter)`  
  `during registration. The system shall authenticate users securely using encrypted`  
  `credentials, and TPO Administrators shall have the ability to approve or deny new`  
  `user registrations before granting access. During the registration process, Students`  
  `shall be required to provide their academic details and link their resumes, while`  
  `Company Recruiters shall be required to provide their company information.[span_44](start_span)[span_44](end_span)`  
`• Priority: High[span_45](start_span)[span_45](end_span)`  
`• Dependencies: Database user tables, secure encryption libraries.[span_46](start_span)[span_46](end_span)`

`FR-002: Job Posting and Management[span_47](start_span)[span_47](end_span)`  
`• Description: Company Recruiters shall be able to post, edit, and delete job`  
  `openings with details like description, eligibility criteria, and deadlines. TPO`  
  `Administrators must approve all new job postings before they are visible to`  
  `students.[span_48](start_span)[span_48](end_span)`  
`• Priority: High[span_49](start_span)[span_49](end_span)`  
`• Dependencies: FR-001.[span_50](start_span)[span_50](end_span)`

`FR-003: Job Application and Tracking[span_51](start_span)[span_51](end_span)`  
`• Description: Students shall be able to search, filter, and apply for approved job`  
  `postings. They must be able to track the status of their applications (e.g., Applied,`  
  `Shortlisted, Interview Scheduled, Hired).[span_52](start_span)[span_52](end_span)`  
`• Priority: High[span_53](start_span)[span_53](end_span)`  
`• Dependencies: FR-001, FR-002.[span_54](start_span)[span_54](end_span)`

`FR-004: Administrative Dashboard and Reporting[span_55](start_span)[span_55](end_span)`  
`• Description: The TPO Administrator shall have a dashboard to view system`  
  `statistics, manage users and job postings, and generate reports on placement`  
  `activities.[span_56](start_span)[span_56](end_span)`  
`• Priority: High[span_57](start_span)[span_57](end_span)`  
`• Dependencies: FR-001, FR-002, FR-003.[span_58](start_span)[span_58](end_span)`

`FR-005: Notification System[span_59](start_span)[span_59](end_span)`  
`• Description: The system shall send automated email notifications for key events,`  
  `such as new job postings, application status changes, and interview schedules.[span_60](start_span)[span_60](end_span)`  
`• Priority: Medium[span_61](start_span)[span_61](end_span)`  
`• Dependencies: FR-001, FR-002 and FR-003.[span_62](start_span)[span_62](end_span)`

`--------------------------------------------------------------------------------`  
`2.2 Non-Functional Requirements[span_63](start_span)[span_63](end_span)`  
`--------------------------------------------------------------------------------`

`Performance:[span_64](start_span)[span_64](end_span)`  
`• Response Time: Page load times should be under 3 seconds. API responses should`  
  `be delivered within 1000ms under normal load.[span_65](start_span)[span_65](end_span)`  
`• Throughput: The system must be capable of handling at least 100 requests per`  
  `second (RPS) during peak load times without degrading the user experience.[span_66](start_span)[span_66](end_span)`  
`• Scalability: The system should be able to handle many concurrent users without`  
  `significant performance degradation.[span_67](start_span)[span_67](end_span)`

`Security:[span_68](start_span)[span_68](end_span)`  
`• Authentication: Passwords must be hashed and salted. User sessions should be`  
  `managed securely.[span_69](start_span)[span_69](end_span)`  
`• Authorization: Users must only be able to access data and functionality permitted`  
  `by their assigned role.[span_70](start_span)[span_70](end_span)`  
`• Data Protection: All sensitive data should be protected against common web`  
  `vulnerabilities like SQL injection and XSS.[span_71](start_span)[span_71](end_span)`

`Usability:[span_72](start_span)[span_72](end_span)`  
`• User Interface: The interface should be intuitive, clean, and responsive, providing`  
  `a seamless experience on both desktop and mobile devices.[span_73](start_span)[span_73](end_span)`  
`• Accessibility: The application should adhere to basic web accessibility standards`  
  `(WCAG).[span_74](start_span)[span_74](end_span)`  
`• User Experience: The application should provide clear, consistent feedback for`  
  `user actions (e.g., loading states, success messages, and error notifications).`  
  `Workflows should be logical and efficient, minimizing the number of clicks`  
  `required to accomplish primary tasks.[span_75](start_span)[span_75](end_span)`

`--------------------------------------------------------------------------------`  
`2.3 Data Requirements[span_76](start_span)[span_76](end_span)`  
`--------------------------------------------------------------------------------`

`Data Entities: TPO Admin, Student, Company Recruiter, Job Posting, Application[span_77](start_span)[span_77](end_span)`

`• TPOAdmin: Represents a Training and Placement Officer who manages`  
  `approvals, monitors student and recruiter accounts, and oversees job postings.`  
  `Holds a specific admin role.[span_78](start_span)[span_78](end_span)`  
  `Attributes:`  
  `- TPO_ID: Unique TPO ID[span_79](start_span)[span_79](end_span)`  
  `- Name: TPO full name[span_80](start_span)[span_80](end_span)`  
  `- Email: TPO email address[span_81](start_span)[span_81](end_span)`  
  `- Password: Password hash[span_82](start_span)[span_82](end_span)`  
  `- Role: User role type[span_83](start_span)[span_83](end_span)`

`• Student: Represents a student registered in the system, including personal details,`  
  `email/password credentials, academic records, and their application history. Tracks`  
  `the current account status for approval workflows.[span_84](start_span)[span_84](end_span)`  
  `Attributes:`  
  `- Student_ID: Unique student ID[span_85](start_span)[span_85](end_span)`  
  `- Name: Student full name[span_86](start_span)[span_86](end_span)`  
  `- Faculty_No: Faculty number[span_87](start_span)[span_87](end_span)`  
  `- Enrollment_No: Enrollment number[span_88](start_span)[span_88](end_span)`  
  `- Email: Student email address[span_89](start_span)[span_89](end_span)`  
  `- Password: Password hash[span_90](start_span)[span_90](end_span)`  
  `- Academic_Records: Academic details JSON[span_91](start_span)[span_91](end_span)`  
  `- Account_Status: Account approval status[span_92](start_span)[span_92](end_span)`

`• Company Recruiter: Represents a recruiter or company user who can post job`  
  `openings, manage company details, and track the approval status of their account.`  
  `Linked to multiple job postings.[span_93](start_span)[span_93](end_span)`  
  `Attributes:`  
  `- Recruiter_ID: Unique recruiter ID[span_94](start_span)[span_94](end_span)`  
  `- Name: Recruiter full name[span_95](start_span)[span_95](end_span)`  
  `- Email: Recruiter email address[span_96](start_span)[span_96](end_span)`  
  `- Password: Password hash[span_97](start_span)[span_97](end_span)`  
  `- Company_Profile: Company description[span_98](start_span)[span_98](end_span)`  
  `- Account_Status: Account approval status[span_99](start_span)[span_99](end_span)`

`• JobPosting: Represents a job opportunity posted by a recruiter, including`  
  `description, eligibility criteria, application deadline, and approval status. Connected`  
  `to multiple student applications.[span_100](start_span)[span_100](end_span)`  
  `Attributes:`  
  `- Job_ID: Unique job ID[span_101](start_span)[span_101](end_span)`  
  `- Recruiter_ID: Posting recruiter ID[span_102](start_span)[span_102](end_span)`  
  `- Eligibility_Criteria: Eligibility requirements[span_103](start_span)[span_103](end_span)`  
  `- Job_Description: Job details[span_104](start_span)[span_104](end_span)`  
  `- Application_Deadline: Application cutoff date[span_105](start_span)[span_105](end_span)`  
  `- Approval_Status: Posting approval status[span_106](start_span)[span_106](end_span)`

`• Application: Represents a student's application for a job posting, tracking which`  
  `student applied to which job and the current status of the application.[span_107](start_span)[span_107](end_span)`  
  `Attributes:`  
  `- Application_ID: Unique application ID[span_108](start_span)[span_108](end_span)`  
  `- Job_ID: Linked job ID[span_109](start_span)[span_109](end_span)`  
  `- Student_ID: Applicant student ID[span_110](start_span)[span_110](end_span)`  
  `- Application_Status: Application approval status[span_111](start_span)[span_111](end_span)`

`Data Relationships:[span_112](start_span)[span_112](end_span)`  
`• A TPO Admin manages many Students (One-to-Many).[span_113](start_span)[span_113](end_span)`  
`• A TPO Admin verifies many Company Recruiters (One-to-Many).[span_114](start_span)[span_114](end_span)`  
`• A TPO Admin approves many Job Postings (One-to-Many).[span_115](start_span)[span_115](end_span)`  
`• A Company Recruiter posts many Job Postings (One-to-Many).[span_116](start_span)[span_116](end_span)`  
`• A Company Recruiter Updates Status of many Applications (One-to-Many).[span_117](start_span)[span_117](end_span)`  
`• A Student submits many Applications (One-to-Many).[span_118](start_span)[span_118](end_span)`  
`• A Job Posting receives many Applications (One-to-Many).[span_119](start_span)[span_119](end_span)`

`Data Volume and Growth:[span_120](start_span)[span_120](end_span)`  
`The system is expected to store data for dozens of students and companies, with data volume`  
`growing each academic year. The database should be designed to handle this growth.[span_121](start_span)[span_121](end_span)`

`--------------------------------------------------------------------------------`  
`2.4 System Requirements[span_122](start_span)[span_122](end_span)`  
`--------------------------------------------------------------------------------`

`Software Requirements:[span_123](start_span)[span_123](end_span)`  
`• Operating System: The application is platform-independent for the end-user. It`  
  `can be accessed from any modern operating system that supports a compatible web`  
  `browser, including Windows, macOS, Linux, iOS, and Android.[span_124](start_span)[span_124](end_span)`  
`• Browser Support: The web application must be compatible with the latest versions`  
  `of modern browsers like Chrome, Firefox, Safari, and Edge.[span_125](start_span)[span_125](end_span)`  
`• Third-party Integrations: The system will integrate with an email service called`  
  `EmailJS provider for sending notifications.[span_126](start_span)[span_126](end_span)`

`Hardware Requirements:[span_127](start_span)[span_127](end_span)`  
`• Server: The application will be deployed on Vercel's serverless infrastructure,`  
  `which handles server specifications and scaling automatically.[span_128](start_span)[span_128](end_span)`  
`• Client Device Requirements: Any modern device capable of running a supported`  
  `web browser is sufficient. This includes standard desktops, laptops, tablets, and`  
  `smartphones. No special hardware is required.[span_129](start_span)[span_129](end_span)`  
`• Network Infrastructure: A stable broadband or mobile data connection is`  
  `required for clients to access and interact with the application.[span_130](start_span)[span_130](end_span)`

`================================================================================`  
`3. DESIGN AND ANALYSIS[span_131](start_span)[span_131](end_span)`  
`================================================================================`

`3.1 System Architecture[span_132](start_span)[span_132](end_span)`

`High-Level Architecture:[span_133](start_span)[span_133](end_span)`  
`The project follows a three-tier architecture:[span_134](start_span)[span_134](end_span)`  
`1. Presentation Tier (Frontend): A modern, responsive user interface built with Next.js and`  
   `Tailwind CSS.[span_135](start_span)[span_135](end_span)`  
`2. Logic Tier (Backend): A Node.js backend integrated within Next.js API routes to handle`  
   `business logic and API requests.[span_136](start_span)[span_136](end_span)`  
`3. Data Tier (Storage): A PostgreSQL database managed with the Prisma ORM for type-`  
   `safe and efficient data access.[span_137](start_span)[span_137](end_span)`

`Deployment & Component Architecture Overview:[span_138](start_span)[span_138](end_span)[span_139](start_span)[span_139](end_span)`  
`- Hosted on Vercel Serverless Platform:[span_140](start_span)[span_140](end_span)`  
  `• Clients: TPO Admin Client, Student Client, Company Recruiter Client.[span_141](start_span)[span_141](end_span)`  
  `• Frontend Layer: TPO Admin Side Frontend, Student Side Frontend, Company Recruiter Frontend.[span_142](start_span)[span_142](end_span)`  
  `• Backend Layer (Next.js API Routes): Admin Panel & Analytics, TPO Admin Approval Required,`  
    `Student Job & Application Management, Student User & Profile Management, Company Recruiter &`  
    `Profile Management, Company Recruiter Job & Application Management, Email Notifications.[span_143](start_span)[span_143](end_span)`  
  `• Data Access: Prisma ORM connected to PostgreSQL Database Storage.[span_144](start_span)[span_144](end_span)[span_145](start_span)[span_145](end_span)`  
  `• External Services: EmailJS for email notifications.[span_146](start_span)[span_146](end_span)`

`Database Design:[span_147](start_span)[span_147](end_span)`  
`Entity-Relationship: The database schema will consist of tables for TPO Admin, Student,`  
`Company Recruiter, Job, and Application. Relationships will be defined with foreign keys`  
`to ensure data integrity.[span_148](start_span)[span_148](end_span)`

`Normalized Tables (3NF Schema):[span_149](start_span)[span_149](end_span)[span_150](start_span)[span_150](end_span)`

`Table: TPOAdmin[span_151](start_span)[span_151](end_span)`  
`------------------------------------------------------------------------------------------------------`  
`Column       | Type | Constraints                    | Description[span_152](start_span)[span_152](end_span)`  
`------------------------------------------------------------------------------------------------------`  
`TPO ID       | TEXT | PRIMARY KEY                    | Unique TPO ID[span_153](start_span)[span_153](end_span)`  
`Name         | TEXT | NOT NULL                       | Full name[span_154](start_span)[span_154](end_span)`  
`Email        | TEXT | UNIQUE, NOT NULL               | Email address[span_155](start_span)[span_155](end_span)`  
`Password     | TEXT | NOT NULL                       | Password hash[span_156](start_span)[span_156](end_span)`  
`Role         | TEXT | DEFAULT 'TPO_ADMIN', NOT NULL  | User role type[span_157](start_span)[span_157](end_span)`  
`------------------------------------------------------------------------------------------------------`

`Table: Student[span_158](start_span)[span_158](end_span)`  
`------------------------------------------------------------------------------------------------------`  
`Column           | Type  | Constraints              | Description[span_159](start_span)[span_159](end_span)`  
`------------------------------------------------------------------------------------------------------`  
`Student ID       | TEXT  | PRIMARY KEY              | Unique student ID[span_160](start_span)[span_160](end_span)`  
`Name             | TEXT  | NOT NULL                 | Full name[span_161](start_span)[span_161](end_span)`  
`Faculty_No       | TEXT  | NULL                     | Faculty number[span_162](start_span)[span_162](end_span)`  
`Enrollment No    | TEXT  | NULL                     | Enrollment number[span_163](start_span)[span_163](end_span)`  
`Email            | TEXT  | UNIQUE, NOT NULL         | Email address[span_164](start_span)[span_164](end_span)`  
`Password         | TEXT  | NOT NULL                 | Password hash[span_165](start_span)[span_165](end_span)`  
`Academic Records | JSONB | NULL                     | Academic details[span_166](start_span)[span_166](end_span)`  
`Account Status   | TEXT  | DEFAULT 'PENDING STUDENT'| Approval status[span_167](start_span)[span_167](end_span)`  
`------------------------------------------------------------------------------------------------------`

`Table: Company Recruiter[span_168](start_span)[span_168](end_span)`  
`------------------------------------------------------------------------------------------------------`  
`Column          | Type | Constraints                | Description[span_169](start_span)[span_169](end_span)`  
`------------------------------------------------------------------------------------------------------`  
`Recruiter ID    | TEXT | PRIMARY KEY                | Unique recruiter ID[span_170](start_span)[span_170](end_span)`  
`Name            | TEXT | NOT NULL                   | Full name[span_171](start_span)[span_171](end_span)`  
`Email           | TEXT | UNIQUE, NOT NULL           | Email address[span_172](start_span)[span_172](end_span)`  
`Password        | TEXT | NOT NULL                   | Password hash[span_173](start_span)[span_173](end_span)`  
`Company_Profile | TEXT | NULL                       | Company description[span_174](start_span)[span_174](end_span)`  
`Account Status  | TEXT | DEFAULT 'PENDING RECRUITER'| Approval status[span_175](start_span)[span_175](end_span)`  
`------------------------------------------------------------------------------------------------------`

`Table: Job Posting[span_176](start_span)[span_176](end_span)`  
`---------------------------------------------------------------------------------------------------------------------------------`  
`Column               | Type      | Constraints                                      | Description[span_177](start_span)[span_177](end_span)`  
`---------------------------------------------------------------------------------------------------------------------------------`  
`Job ID               | TEXT      | PRIMARY KEY                                      | Unique job ID[span_178](start_span)[span_178](end_span)`  
`Recruiter ID         | TEXT      | FOREIGN KEY -> Company Recruiter(Recruiter_ID)   | Posting recruiter ID[span_179](start_span)[span_179](end_span)`  
`Eligibility_Criteria | TEXT      | NULL                                             | Eligibility rules[span_180](start_span)[span_180](end_span)`  
`Job_Description      | TEXT      | NOT NULL                                         | Job details[span_181](start_span)[span_181](end_span)`  
`Application_Deadline | TIMESTAMP | NOT NULL                                         | Application cutoff[span_182](start_span)[span_182](end_span)`  
`Approval_Status      | TEXT      | DEFAULT 'PENDING'                                | Posting approval[span_183](start_span)[span_183](end_span)`  
`---------------------------------------------------------------------------------------------------------------------------------`

`Table: Application[span_184](start_span)[span_184](end_span)`  
`------------------------------------------------------------------------------------------------------------------------`  
`Column             | Type | Constraints                            | Description[span_185](start_span)[span_185](end_span)`  
`------------------------------------------------------------------------------------------------------------------------`  
`Application_ID     | TEXT | PRIMARY KEY                            | Unique application ID[span_186](start_span)[span_186](end_span)`  
`Job ID             | TEXT | FOREIGN KEY -> JobPosting(Job_ID)      | Linked job ID[span_187](start_span)[span_187](end_span)`  
`Student ID         | TEXT | FOREIGN KEY -> Student(Student_ID)     | Applicant student ID[span_188](start_span)[span_188](end_span)`  
`Application_Status | TEXT | DEFAULT 'PENDING'                      | Application approval[span_189](start_span)[span_189](end_span)`  
`------------------------------------------------------------------------------------------------------------------------`

`Schema Normalization:[span_190](start_span)[span_190](end_span)`  
`Schema is already normalized, specifically it meets 3NF (Third Normal Form) standards.[span_191](start_span)[span_191](end_span)`  
`1. 1NF (Atomic values): All fields contain atomic (indivisible) values.[span_192](start_span)[span_192](end_span)[span_193](start_span)[span_193](end_span)`  
`2. 2NF (No partial dependency): All non-key attributes are fully functionally dependent on the`  
   `primary key of their table (Every non-key column depends entirely on the table's primary key).[span_194](start_span)[span_194](end_span)`  
   `For example, in Student, Email, Name, Faculty_No all depend on Student_ID.[span_195](start_span)[span_195](end_span)`  
`3. 3NF (No transitive dependency): No non-key attribute depends on another non-key attribute`  
   `(Non-key columns do not depend on other non-key columns). For instance, in JobPosting,`  
   `Recruiter_ID is a foreign key, and other attributes depend only on Job_ID.[span_196](start_span)[span_196](end_span)`

`Indexes and Constraints:[span_197](start_span)[span_197](end_span)`  
`To keep our data clean and make the application run fast, we'll rely on two key tools: indexes`  
`and constraints. Indexes act like a book's index, helping the database find information quickly`  
`without having to search through every single record. The database automatically creates indexes`  
`on primary keys to find entries instantly. We will also manually add indexes to foreign keys to`  
`speed up operations that connect related tables. Alongside indexes, constraints are rules that`  
`prevent bad data from being entered. We'll use Primary Keys to ensure every record is unique,`  
`Foreign Keys to properly link our tables, and Unique constraints for fields that can't have duplicates.[span_198](start_span)[span_198](end_span)`

`--------------------------------------------------------------------------------`  
`3.2 Detailed Design Diagram[span_199](start_span)[span_199](end_span)`  
`--------------------------------------------------------------------------------`

`Actors:[span_200](start_span)[span_200](end_span)`  
`1. Student: An individual user seeking job opportunities through the platform.[span_201](start_span)[span_201](end_span)`  
`2. Recruiter: A representative from a company who posts job openings and manages applicants.[span_202](start_span)[span_202](end_span)`  
`3. TPO Admin (Training and Placement Officer Admin): An administrative user who manages and oversees`  
   `the entire placement process, ensuring the integrity of the data and interactions on the platform.[span_203](start_span)[span_203](end_span)`

`Actor Interactions (Use Cases):[span_204](start_span)[span_204](end_span)`

`1. Student:[span_205](start_span)[span_205](end_span)`  
   `• Register with Personal & Academic Details: A new student must register on the platform.`  
     `This action requires (<<include>>) an Admin Approval to be completed.[span_206](start_span)[span_206](end_span)`  
   `• Search for Job: Students can browse available job listings.[span_207](start_span)[span_207](end_span)`  
   `• Filter with Criteria: This is an optional (<<extend>>) function of searching, allowing`  
     `students to narrow down job results based on specific criteria.[span_208](start_span)[span_208](end_span)`  
   `• Apply for Job: Once a suitable job is found, the student can apply for it. This process`  
     `mandatorily (<<include>>) involves the system running a Confirm Eligibility Criteria check.[span_209](start_span)[span_209](end_span)`  
   `• View Application Status: Students can track the status of their job applications`  
     `(e.g., submitted, under review, shortlisted).[span_210](start_span)[span_210](end_span)`

`2. Recruiter:[span_211](start_span)[span_211](end_span)`  
   `• Register: A new recruiter must create a profile on the system. This registration process`  
     `requires (<<include>>) the TPO Admin to Verify Recruiter Profile.[span_212](start_span)[span_212](end_span)`  
   `• Post Jobs: Registered recruiters can post new job openings. This action always (<<include>>)`  
     `requires them to Fill Job Details. The posted job is then sent to the TPO Admin for approval.[span_213](start_span)[span_213](end_span)`  
   `• View Applications: Recruiters can view the list of students who have applied to their posted jobs.[span_214](start_span)[span_214](end_span)`  
   `• Update Status of Applicants: They can manage the application pipeline by updating the status`  
     `of each applicant (e.g., Shortlisted, Interview Scheduled, Rejected, Hired).[span_215](start_span)[span_215](end_span)`

`3. TPO Admin:[span_216](start_span)[span_216](end_span)`  
   `• Verify Student Details: The admin is responsible for verifying the information provided`  
     `by students during their registration.[span_217](start_span)[span_217](end_span)`  
   `• Admin Approval: This is a core function linked to student registration, where the admin`  
     `approves a student's profile, allowing them to access the system.[span_218](start_span)[span_218](end_span)`  
   `• Verify Recruiter Profile: The admin validates the profiles of new recruiters before they`  
     `are allowed to post jobs.[span_219](start_span)[span_219](end_span)`  
   `• Approve/Reject job postings: The admin reviews job postings submitted by recruiters. This`  
     `review process (<<include>>) requires them to Review Job Details before making a decision.[span_220](start_span)[span_220](end_span)`  
   `• Generate Report: The admin can create reports about placement activities and can choose`  
     `either the PDF generation or Excel generation.[span_221](start_span)[span_221](end_span)`  
   `• Filter By Criteria: This is an optional (<<extend>>) feature that allows the admin to`  
     `generate more specific reports by applying filters.[span_222](start_span)[span_222](end_span)`

`Data Flow Diagrams (DFD) Summary:[span_223](start_span)[span_223](end_span)`

`• Context Diagram:[span_224](start_span)[span_224](end_span)`  
  `- Entities: Student, Company Recruiter, TPO Admin, PlacementConnect System.[span_225](start_span)[span_225](end_span)`  
  `- Student flows: Register, Search for Jobs / Apply & Track Status, receives Student Registration Approved,`  
    `Status of Applied Jobs.[span_226](start_span)[span_226](end_span)`  
  `- Company Recruiter flows: Register, Post Job / View Applicants & Update Status, receives Registration Approved,`  
    `Job Post Approval & Applicants Status Updated.[span_227](start_span)[span_227](end_span)`  
  `- TPO Admin flows: Provides pending student/recruiter registration approvals, receives student/recruiter`  
    `registrations approved; provides all job post approval requests, receives job posts approved; requests`  
    `and receives generated reports.[span_228](start_span)[span_228](end_span)`

`• Level 0 DFD:[span_229](start_span)[span_229](end_span)`  
  `- 0.0 Process: TPO Admin Login (Enter login details, verify credentials).[span_230](start_span)[span_230](end_span)`  
  `- 1.0 Process: Manage Student Account (Handles student registration, submits for verification,`  
    `updates account on approval).[span_231](start_span)[span_231](end_span)`  
  `- 2.0 Process: Logged-in Student Manage Jobs & Applications (Search jobs, view filtered jobs,`  
    `apply, store application, view application status).[span_232](start_span)[span_232](end_span)`  
  `- 3.0 Process: Manage Company Recruiter Account (Register recruiter details, submit for verification,`  
    `update status upon approval).[span_233](start_span)[span_233](end_span)`  
  `- 4.0 Process: Logged-in Company Recruiter Manages Job Postings & Applications (Post job details,`  
    `send for approval, fetch applicants, update application status, inform students).[span_234](start_span)[span_234](end_span)`

`• Level 1 DFDs:[span_235](start_span)[span_235](end_span)`  
  `- Process 1.0 (Student Registration):[span_236](start_span)[span_236](end_span)`  
    `1.1 Register Student Details -> 1.2 Verify Student Details (by TPO Admin) -> 1.3 Update Account Status ->`  
    `1.4 Approved Student Logged In.[span_237](start_span)[span_237](end_span)`  
  `- Process 2.0 (Job Search & Application):[span_238](start_span)[span_238](end_span)`  
    `2.1 Search For Jobs (Query Job Postings Data Store) -> 2.2 Submit Application (Write to Applications Data Store) ->`  
    `2.3 Track Application (Read status from Applications Data Store).[span_239](start_span)[span_239](end_span)`  
  `- Process 3.0 (Recruiter Registration):[span_240](start_span)[span_240](end_span)`  
    `3.1 Register Recruiter Details -> 3.2 Verify Recruiter Details (by TPO Admin) -> 3.3 Update Account Status ->`  
    `3.4 Approved Company Recruiter Logged In.[span_241](start_span)[span_241](end_span)`  
  `- Process 4.0 (Job Posting & Application Review):[span_242](start_span)[span_242](end_span)`  
    `4.1 Post Job -> 4.2 Approve Job Posting (by TPO Admin) -> 4.3 Inform Recruiter -> 4.4 Update Application`  
    `Status of Students -> 4.5 Inform Student Of Application Status Update.[span_243](start_span)[span_243](end_span)`

`Class Diagram Specifications:[span_244](start_span)[span_244](end_span)`

`• Class: CompanyRecruiter[span_245](start_span)[span_245](end_span)`  
  `Attributes:`  
  `- recruiterID: String[span_246](start_span)[span_246](end_span)`  
  `- name: String[span_247](start_span)[span_247](end_span)`  
  `- email: String[span_248](start_span)[span_248](end_span)`  
  `- password: String[span_249](start_span)[span_249](end_span)`  
  `- companyProfile: String[span_250](start_span)[span_250](end_span)`  
  `- accountStatus: String[span_251](start_span)[span_251](end_span)`  
  `Methods:`  
  `+ postJob(jobData: NewJobData): Promise<JobPosting>[span_252](start_span)[span_252](end_span)`  
  `+ manageJob(jobID: String): Promise<JobPosting>[span_253](start_span)[span_253](end_span)`  
  `+ viewApplicants(jobID: int): Promise<Array<Student>>[span_254](start_span)[span_254](end_span)`  
  `+ updateApplicationStatus(applicationID: int, applicationStatus: String): Promise<Application>[span_255](start_span)[span_255](end_span)`

`• Class: TPOAdmin[span_256](start_span)[span_256](end_span)`  
  `Attributes:`  
  `- tpoID: String[span_257](start_span)[span_257](end_span)`  
  `- name: String[span_258](start_span)[span_258](end_span)`  
  `- email: String[span_259](start_span)[span_259](end_span)`  
  `- password: String[span_260](start_span)[span_260](end_span)`  
  `- role: String[span_261](start_span)[span_261](end_span)`  
  `Methods:`  
  `+ verifyStudentAccount(studentId: int): Promise<Student>[span_262](start_span)[span_262](end_span)`  
  `+ verifyRecruiterAccount(recruiterID: String): Promise<CompanyRecruiter>[span_263](start_span)[span_263](end_span)`  
  `+ approveJobPostings(jobID: String): Promise<JobPosting>[span_264](start_span)[span_264](end_span)`  
  `+ viewReports(reportOptions: ReportOptions): Promise<ReportData>[span_265](start_span)[span_265](end_span)`

`• Class: Student[span_266](start_span)[span_266](end_span)`  
  `Attributes:`  
  `- studentID: String[span_267](start_span)[span_267](end_span)`  
  `- name: String[span_268](start_span)[span_268](end_span)`  
  `- facultyNo: String[span_269](start_span)[span_269](end_span)`  
  `- enrollmentNo: String[span_270](start_span)[span_270](end_span)`  
  `- email: String[span_271](start_span)[span_271](end_span)`  
  `- password: String[span_272](start_span)[span_272](end_span)`  
  `- academicRecords: JSON[span_273](start_span)[span_273](end_span)`  
  `- accountStatus: String[span_274](start_span)[span_274](end_span)`  
  `- applications: List<Application>[span_275](start_span)[span_275](end_span)`  
  `Methods:`  
  `+ updateProfile(profileData: Student): Promise<Student>[span_276](start_span)[span_276](end_span)`  
  `+ searchJobs(filters: JobSearchFilters): Promise<Array<JobPosting>>[span_277](start_span)[span_277](end_span)`  
  `+ applyForJobs(jobID: String): Promise<Application>[span_278](start_span)[span_278](end_span)`  
  `+ viewApplicationStatus(applicationID: String): Promise<Application>[span_279](start_span)[span_279](end_span)`

`• Class: JobPosting[span_280](start_span)[span_280](end_span)`  
  `Attributes:`  
  `- jobID: String[span_281](start_span)[span_281](end_span)`  
  `- jobDescription: String[span_282](start_span)[span_282](end_span)`  
  `- applicationDeadline: DateTime[span_283](start_span)[span_283](end_span)`  
  `- eligibilityCriteria: String[span_284](start_span)[span_284](end_span)`  
  `- approvalStatus: String[span_285](start_span)[span_285](end_span)`  
  `- applications: List<Application>[span_286](start_span)[span_286](end_span)`

`• Class: Application[span_287](start_span)[span_287](end_span)`  
  `Attributes:`  
  `- applicationID: String[span_288](start_span)[span_288](end_span)`  
  `- applicationStatus: String[span_289](start_span)[span_289](end_span)`

`Sequence Diagrams Summary:[span_290](start_span)[span_290](end_span)`

`• sd TPO Admin:[span_291](start_span)[span_291](end_span)`  
  `1.0 Enter Login Details -> 1.1 Successful Login.[span_292](start_span)[span_292](end_span)`  
  `2.0 Review Pending Student Approval Requests -> 2.1 Show Student Details.[span_293](start_span)[span_293](end_span)`  
      `[alt: Approve -> 2.1.1 Approve Student Registration -> 2.1.2 Notify New Student Approved][span_294](start_span)[span_294](end_span)`  
      `[alt: Decline -> 2.2 Decline Student Registration -> 2.3 Notify Student Declined][span_295](start_span)[span_295](end_span)`  
  `3.0 Review Pending Recruiter Approval Requests -> 3.1 Show Recruiter Details.[span_296](start_span)[span_296](end_span)`  
      `[alt: Approve -> 3.1.1 Approve Recruiter Registration -> 3.1.2 Notify New Recruiter Approved][span_297](start_span)[span_297](end_span)`  
      `[alt: Decline -> 3.2 Decline Recruiter Registration -> 3.3 Notify Recruiter Declined][span_298](start_span)[span_298](end_span)`  
  `4.1 Review Job Postings -> 4.2 Show Job Details.[span_299](start_span)[span_299](end_span)`  
      `[alt: Approve -> 4.2.1 Approve Job Posting -> 4.2.2 Notify Job Posting Approved & Live][span_300](start_span)[span_300](end_span)`  
      `[alt: Decline -> 4.3 Decline Job Posting -> 4.4 Notify Job Posting Declined][span_301](start_span)[span_301](end_span)`  
  `5.0 Generate Placement Report -> 5.1 Provide Report.[span_302](start_span)[span_302](end_span)`  
  `6.0 Logout -> 6.1 Notify Successfully Logged Out.[span_303](start_span)[span_303](end_span)`

`• sd Student:[span_304](start_span)[span_304](end_span)`  
  `1.0 Enter Login Details.[span_305](start_span)[span_305](end_span)`  
  `[alt: Student Account Already Exists == True][span_306](start_span)[span_306](end_span)`  
      `1.1 Notify Approved Account is Logged in.[span_307](start_span)[span_307](end_span)`  
      `1.2 Search For Job -> 1.3 Display Filtered Job Listings.[span_308](start_span)[span_308](end_span)`  
      `1.4 Apply For Job -> 1.5 Application Submission Acknowledgement.[span_309](start_span)[span_309](end_span)`  
      `1.6 View Application Status -> 1.7 Display Current Status of Application.[span_310](start_span)[span_310](end_span)`  
      `1.8 Logout -> 1.9 Successfully Logged Out.[span_311](start_span)[span_311](end_span)`  
  `[alt: Student Account Already Exists == False][span_312](start_span)[span_312](end_span)`  
      `2.0 Notify: No Account Found. Enter Registration Details.[span_313](start_span)[span_313](end_span)`  
      `2.1 Register With Personal & Academic Details -> 2.2 Notify New Student Registration For Verification.[span_314](start_span)[span_314](end_span)`  
      `[alt: Decision == Approve -> 2.2.1 Student Registration Approved -> 2.2.2 Notify Account Approved & Logged in][span_315](start_span)[span_315](end_span)`  
      `[alt: Decision == Decline -> 3.0 Student Registration Declined -> 3.1 Notify Account Declined][span_316](start_span)[span_316](end_span)`

`• sd Company Recruiter:[span_317](start_span)[span_317](end_span)`  
  `1.0 Enter Login Details.[span_318](start_span)[span_318](end_span)`  
  `[alt: Recruiter Account Already Exists == True][span_319](start_span)[span_319](end_span)`  
      `1.1 Notify Approved Account Logged in.[span_320](start_span)[span_320](end_span)`  
      `1.1.1 Post Job With Details -> 1.1.2 Notify New Job Posting For Approval.[span_321](start_span)[span_321](end_span)`  
      `[alt: Decision == Approve -> 1.1.2.1 Job Posting Approved -> 1.1.2.2 Notify Job Posting Is Live][span_322](start_span)[span_322](end_span)`  
      `[alt: Decision == Decline -> 1.1.3 Job Posting Declined -> 1.1.4 Notify Job Posting Declined][span_323](start_span)[span_323](end_span)`  
      `1.2 View List of Applicants For Posted Jobs -> 1.2.1 Display List of Applicants.[span_324](start_span)[span_324](end_span)`  
      `1.2.2 Update Status of Applicants -> 1.2.3 Notify Application Status Updated.[span_325](start_span)[span_325](end_span)`  
      `1.3 Logout -> 1.3.1 Successfully Logged Out.[span_326](start_span)[span_326](end_span)`  
  `[alt: Recruiter Account Already Exists == False][span_327](start_span)[span_327](end_span)`  
      `2.0 Notify: No Account Found. Enter Registration Details.[span_328](start_span)[span_328](end_span)`  
      `2.1 Register With Details -> 2.2 Notify New Company Recruiter Registration For Verification.[span_329](start_span)[span_329](end_span)`  
      `[alt: Decision == Approve -> 2.2.1 Company Recruiter Registration Approved -> 2.2.2 Account Approved & Logged in][span_330](start_span)[span_330](end_span)`  
      `[alt: Decision == Decline -> 3.0 Company Recruiter Registration Declined -> 3.1 Notify Account Declined][span_331](start_span)[span_331](end_span)`

`--------------------------------------------------------------------------------`  
`3.3 Design Tools and Limitations[span_332](start_span)[span_332](end_span)`  
`--------------------------------------------------------------------------------`

`Modeling Tool: Draw.io was used for creating ER diagrams, use case diagrams, and DFDs.[span_333](start_span)[span_333](end_span)`  
`Purpose: To visualize the system's high-level architecture, Entity Relationship Modeling,`  
`Use Case Diagram, Data Flow Diagram, Classes Diagram and Sequence Diagrams.[span_334](start_span)[span_334](end_span)`

`Limitations: With Draw.io, you must export each diagram as an image and manually paste`  
`it into a document which is a very tedious task. Also, the connectors that automatically`  
`snap to points and route around shapes are powerful, but sometimes they feel`  
`uncontrollable. A user might struggle to make a line go exactly where they want it, fighting`  
`with the tool as it tries to auto-correct the path. This can make the simple act of connecting`  
`two boxes feel like a chore.[span_335](start_span)[span_335](end_span)`

`================================================================================`  
`4. IMPLEMENTATION[span_336](start_span)[span_336](end_span)`  
`================================================================================`

`4.1 Technology Stack Justification[span_337](start_span)[span_337](end_span)`

`Frontend:[span_338](start_span)[span_338](end_span)`  
`• Technology: Next.js (React)[span_339](start_span)[span_339](end_span)`  
`• Justification: Chosen for its features like server-side rendering (SSR) and static`  
  `site generation (SSG), which provide excellent performance and SEO. Its file-based`  
  `routing and API routes simplify development.[span_340](start_span)[span_340](end_span)`  
`• Benefits: Faster page loads, improved developer experience, and a robust ecosystem.[span_341](start_span)[span_341](end_span)`

`Backend:[span_342](start_span)[span_342](end_span)`  
`• Technology: Next.js API Routes (Node.js)[span_343](start_span)[span_343](end_span)`  
`• Justification: Integrating the backend with the frontend in a single framework`  
  `simplifies the architecture and deployment process.[span_344](start_span)[span_344](end_span)`  
`• Benefits: Reduced complexity, seamless data fetching, and a unified codebase.[span_345](start_span)[span_345](end_span)`

`Database:[span_346](start_span)[span_346](end_span)`  
`• Technology: PostgreSQL with Prisma ORM[span_347](start_span)[span_347](end_span)`  
`• Justification: PostgreSQL is a powerful, reliable, and scalable open-source`  
  `relational database. Prisma is chosen for its type safety, auto-generated queries, and`  
  `easy-to-use API, which speeds up development and reduces bugs.[span_348](start_span)[span_348](end_span)`  
`• Benefits: Data integrity, high performance, and a type-safe database layer.[span_349](start_span)[span_349](end_span)`

`--------------------------------------------------------------------------------`  
`4.2 Interface Design[span_350](start_span)[span_350](end_span)`  
`--------------------------------------------------------------------------------`

`Interface Type: A web-based Graphical User Interface (GUI) that is responsive and works`  
`across various devices.[span_351](start_span)[span_351](end_span)`

`Justification: A web-based GUI is chosen for its universal accessibility, allowing all users`  
`to access the platform from any device with an internet connection and a modern browser,`  
`without needing to install any software. This approach simplifies deployment and`  
`maintenance. A responsive design is crucial to ensure a consistent and user-friendly`  
`experience across a multitude of devices, including desktops, laptops, and smartphones.[span_352](start_span)[span_352](end_span)`

`User Interface Screenshots: In Progress.[span_353](start_span)[span_353](end_span)`

`User Manual:[span_354](start_span)[span_354](end_span)`  
`A comprehensive user manual will be developed to guide users through the platform's features.`  
`The manual will be structured by user role and will include:[span_355](start_span)[span_355](end_span)`  
`• Getting Started: Step-by-step instructions for account registration, login procedures,`  
  `and password recovery.[span_356](start_span)[span_356](end_span)`  
`• For Students: Detailed guidance on creating and updating profiles, searching for job postings,`  
  `submitting applications, and tracking application status.[span_357](start_span)[span_357](end_span)`  
`• For Company Recruiters: Instructions on creating a company profile, posting new job openings,`  
  `managing applications, and communicating with candidates.[span_358](start_span)[span_358](end_span)`  
`• For TPO Administrators: A guide to the admin dashboard, including user management, content`  
  `moderation, and generating system reports.[span_359](start_span)[span_359](end_span)`  
`• FAQs: A section addressing common questions.[span_360](start_span)[span_360](end_span)`

`--------------------------------------------------------------------------------`  
`4.3 Implementation Status[span_361](start_span)[span_361](end_span)`  
`--------------------------------------------------------------------------------`

`Completed Features / Feature Status:[span_362](start_span)[span_362](end_span)`  
`1. FR-001: User Account Registration: Provides secure login and registration for Students,`  
   `TPO Administrators, and Company Recruiters with role selection and role-based access`  
   `control. Students provide academic details; recruiters provide company info. TPO approval`  
   `is required for new users.`  
   `Status - In Progress / Being Implemented[span_363](start_span)[span_363](end_span)`

`2. FR-002: Job Posting and Management: Enables Company Recruiters to post, edit, and`  
   `delete job openings, with TPO Administrator approval required before visibility to`  
   `students.`  
   `Status - In Progress / Being Implemented[span_364](start_span)[span_364](end_span)`

`3. FR-003: Job Application and Tracking: Allows Students to search, filter, and apply for`  
   `approved job postings, and track their application status through various stages.`  
   `Status - In Progress / Being Implemented[span_365](start_span)[span_365](end_span)`

`4. FR-004: Administrative Dashboard and Reporting: Provides TPO Administrators a dashboard`  
   `to manage users, job postings, view statistics, and generate placement reports.`  
   `Status - In Progress / Being Implemented[span_366](start_span)[span_366](end_span)`

`5. FR-005: Notification System: Sends automated email notifications for key events,`  
   `including new job postings, application status updates, and interview schedules.`  
   `Status - In Progress / Being Implemented[span_367](start_span)[span_367](end_span)`

`Preliminary Results:[span_368](start_span)[span_368](end_span)`

`Performance Metrics: Upon implementation, the system's performance will be evaluated against`  
`the following key metrics:[span_369](start_span)[span_369](end_span)`  
`• Average Page Load Time: Target time should be as low as possible for all critical pages.[span_370](start_span)[span_370](end_span)`  
`• API Response Time: All backend API endpoints should respond in under 1000ms under typical load.[span_371](start_span)[span_371](end_span)`  
`• Server Uptime: The application will aim for an uptime of 99.9%.[span_372](start_span)[span_372](end_span)`  
`• Database Query Performance: Critical database queries will be optimized to execute efficiently.[span_373](start_span)[span_373](end_span)`

`User Feedback: User feedback is critical for iterative improvement and will be actively collected`  
`during the testing phases through several channels:[span_374](start_span)[span_374](end_span)`  
`• Usability Testing Sessions: Monitored sessions with representative users to identify pain`  
  `points in the UI and workflow.[span_375](start_span)[span_375](end_span)`  
`• Google Form Surveys: Post-usage questionnaires to gauge user satisfaction and ease of use.[span_376](start_span)[span_376](end_span)`

`System Statistics: After deployment, the following system-level statistics will be monitored to`  
`track platform growth and engagement:[span_377](start_span)[span_377](end_span)`  
`• User Engagement: Daily Active Users and Monthly Active Users.[span_378](start_span)[span_378](end_span)`  
`• Content Volume: Total number of registered students, participating companies, and active`  
  `job postings.`  
`• Activity Metrics: Number of job applications submitted per day/week and average applications`  
  `per job posting.`  
