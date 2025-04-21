import streamlit as st
import nltk

# Import for basic NLP
nltk.download('stopwords')
nltk.download('punkt')
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

import pandas as pd
import base64, random
import time, datetime
import pdfplumber
import re
import io
from streamlit_tags import st_tags
from PIL import Image
import pymysql
# Import your course lists
from courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
import plotly.express as px


# Remove pafy and youtube_dl imports since they're having issues

def pdf_reader(file):
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF file: {e}")
    return text


def extract_resume_data(pdf_path):
    """Extract basic information from resume PDF"""
    try:
        import nltk
        nltk.download('punkt')
    except:
        pass
    # Extract text
    text = pdf_reader(pdf_path)

    # Count pages
    with pdfplumber.open(pdf_path) as pdf:
        no_of_pages = len(pdf.pages)

    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    email = emails[0] if emails else ""

    # Extract phone number
    phone_pattern = r'(\+\d{1,3}[-.\s]??)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phones = re.findall(phone_pattern, text)
    phone = phones[0] if phones else ""

    # Extract name (Basic approach - assuming name is in the first few lines)
    lines = text.split('\n')
    name = ""
    for line in lines[:5]:  # Check first 5 lines
        if line and not any(
                keyword in line.lower() for keyword in ['resume', 'cv', 'curriculum', 'email', 'phone', 'address']):
            # Assume first significant line that's not a header might be the name
            name = line.strip()
            break

    # Extract skills - define skill keywords
    skill_keywords = [
        'python', 'java', 'javascript', 'html', 'css', 'react', 'angular', 'node',
        'sql', 'mongodb', 'django', 'flask', 'machine learning', 'ai', 'data science',
        'excel', 'powerpoint', 'word', 'adobe', 'photoshop', 'c++', 'c#', 'php',
        'kubernetes', 'docker', 'aws', 'azure', 'gcp', 'linux', 'bash', 'git',
        'agile', 'scrum', 'project management', 'leadership'
    ]

    # Tokenize the text and find skills
    tokens = word_tokenize(text.lower())
    skills = []

    # Check for single word skills
    for skill in skill_keywords:
        if skill in tokens or skill in text.lower():
            skills.append(skill)

    # Check for multi-word skills
    for skill in skill_keywords:
        if ' ' in skill and skill in text.lower():
            skills.append(skill)

    return {
        'name': name,
        'email': email,
        'mobile_number': phone,
        'skills': skills,
        'no_of_pages': no_of_pages
    }


def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


def course_recommender(course_list):
    st.subheader("**Courses & Certificates🎓 Recommendations**")
    c = 0
    rec_course = []
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
    random.shuffle(course_list)
    for c_name, c_link in course_list:
        c += 1
        st.markdown(f"({c}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if c == no_of_reco:
            break
    return rec_course


def fetch_yt_title(link):
    # Simple fallback since pafy is having issues
    video_id = link.split('v=')[-1]
    return f"YouTube Video (ID: {video_id})"


def get_table_download_link(df, filename, text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href


# Connection setup for database
try:
    connection = pymysql.connect(host='localhost', user='root', password='')
    cursor = connection.cursor()
except Exception as e:
    st.error(f"Database connection error: {e}")
    connection = None
    cursor = None


def insert_data(name, email, res_score, timestamp, no_of_pages, reco_field, cand_level, skills, recommended_skills,
                courses):
    if connection and cursor:
        try:
            DB_table_name = 'user_data'
            insert_sql = "insert into " + DB_table_name + " values (0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            rec_values = (name, email, str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, skills,
                          recommended_skills, courses)
            cursor.execute(insert_sql, rec_values)
            connection.commit()
        except Exception as e:
            st.error(f"Database error: {e}")


def run():
    st.title("Smart Resume Analyser")
    st.sidebar.markdown("# Choose User")
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)

    img = Image.open('./Logo/SRA_Logo.jpg')
    img = img.resize((250, 250))
    st.image(img)

    # Create database and tables if connection exists
    if connection and cursor:
        db_sql = """CREATE DATABASE IF NOT EXISTS SRA;"""
        cursor.execute(db_sql)
        connection.select_db("resume_classifier")

        # Create table
        DB_table_name = 'user_data'
        table_sql = "CREATE TABLE IF NOT EXISTS " + DB_table_name + """
                (ID INT NOT NULL AUTO_INCREMENT,
                 Name varchar(100) NOT NULL,
                 Email_ID VARCHAR(50) NOT NULL,
                 resume_score VARCHAR(8) NOT NULL,
                 Timestamp VARCHAR(50) NOT NULL,
                 Page_no VARCHAR(5) NOT NULL,
                 Predicted_Field VARCHAR(25) NOT NULL,
                 User_level VARCHAR(30) NOT NULL,
                 Actual_skills VARCHAR(300) NOT NULL,
                 Recommended_skills VARCHAR(300) NOT NULL,
                 Recommended_courses VARCHAR(600) NOT NULL,
                 PRIMARY KEY (ID));
                """
        cursor.execute(table_sql)

    if choice == 'Normal User':
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])
        if pdf_file is not None:
            save_image_path = './Uploaded_Resumes/' + pdf_file.name
            with open(save_image_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            show_pdf(save_image_path)

            # Use our custom function instead of ResumeParser
            resume_data = extract_resume_data(save_image_path)

            if resume_data:
                # Get the whole resume text
                resume_text = pdf_reader(save_image_path)

                st.header("**Resume Analysis**")
                st.success("Hello " + resume_data['name'])
                st.subheader("**Your Basic info**")
                try:
                    st.text('Name: ' + resume_data['name'])
                    st.text('Email: ' + resume_data['email'])
                    st.text('Contact: ' + resume_data['mobile_number'])
                    st.text('Resume pages: ' + str(resume_data['no_of_pages']))
                except:
                    pass

                # Determine candidate level based on page count
                cand_level = ''
                if resume_data['no_of_pages'] == 1:
                    cand_level = "Fresher"
                    st.markdown('''<h4 style='text-align: left; color: #d73b5c;'>You are looking Fresher.</h4>''',
                                unsafe_allow_html=True)
                elif resume_data['no_of_pages'] == 2:
                    cand_level = "Intermediate"
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>''',
                                unsafe_allow_html=True)
                elif resume_data['no_of_pages'] >= 3:
                    cand_level = "Experienced"
                    st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at experience level!''',
                                unsafe_allow_html=True)

                # Skills section
                st.subheader("**Skills Recommendation💡**")
                keywords = st_tags(label='### Skills that you have', text='See our skills recommendation',
                                   value=resume_data['skills'], key='1')

                # Field recommendation logic
                ds_keyword = ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep Learning', 'flask',
                              'streamlit']
                web_keyword = ['react', 'django', 'node jS', 'react js', 'php', 'laravel', 'magento', 'wordpress',
                               'javascript', 'angular js', 'c#', 'flask']
                android_keyword = ['android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy']
                ios_keyword = ['ios', 'ios development', 'swift', 'cocoa', 'cocoa touch', 'xcode']
                uiux_keyword = ['ux', 'adobe xd', 'figma', 'zeplin', 'balsamiq', 'ui', 'prototyping', 'wireframes',
                                'storyframes', 'adobe photoshop', 'photoshop', 'editing', 'adobe illustrator',
                                'illustrator', 'adobe after effects', 'after effects', 'adobe premier pro',
                                'premier pro', 'adobe indesign', 'indesign', 'wireframe', 'solid', 'grasp',
                                'user research', 'user experience']

                recommended_skills = []
                reco_field = ''
                rec_course = ''

                # Find skills and recommend based on keywords
                for skill in resume_data['skills']:
                    skill_lower = skill.lower()

                    # Data science recommendation
                    if skill_lower in ds_keyword:
                        reco_field = 'Data Science'
                        st.success("** Our analysis says you are looking for Data Science Jobs.**")
                        recommended_skills = ['Data Visualization', 'Predictive Analysis', 'Statistical Modeling',
                                              'Data Mining', 'Clustering & Classification', 'Data Analytics',
                                              'Quantitative Analysis', 'Web Scraping', 'ML Algorithms', 'Keras',
                                              'Pytorch', 'Probability', 'Scikit-learn', 'Tensorflow', "Flask",
                                              'Streamlit']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                       text='Recommended skills generated from System',
                                                       value=recommended_skills, key='2')
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        rec_course = course_recommender(ds_course)
                        break

                    # Web development recommendation
                    elif skill_lower in web_keyword:
                        reco_field = 'Web Development'
                        st.success("** Our analysis says you are looking for Web Development Jobs **")
                        recommended_skills = ['React', 'Django', 'Node JS', 'React JS', 'php', 'laravel', 'Magento',
                                              'wordpress', 'Javascript', 'Angular JS', 'c#', 'Flask', 'SDK']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                       text='Recommended skills generated from System',
                                                       value=recommended_skills, key='3')
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        rec_course = course_recommender(web_course)
                        break

                    # Android App Development
                    elif skill_lower in android_keyword:
                        reco_field = 'Android Development'
                        st.success("** Our analysis says you are looking for Android App Development Jobs **")
                        recommended_skills = ['Android', 'Android development', 'Flutter', 'Kotlin', 'XML', 'Java',
                                              'Kivy', 'GIT', 'SDK', 'SQLite']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                       text='Recommended skills generated from System',
                                                       value=recommended_skills, key='4')
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        rec_course = course_recommender(android_course)
                        break

                    # IOS App Development
                    elif skill_lower in ios_keyword:
                        reco_field = 'IOS Development'
                        st.success("** Our analysis says you are looking for IOS App Development Jobs **")
                        recommended_skills = ['IOS', 'IOS Development', 'Swift', 'Cocoa', 'Cocoa Touch', 'Xcode',
                                              'Objective-C', 'SQLite', 'Plist', 'StoreKit', "UI-Kit", 'AV Foundation',
                                              'Auto-Layout']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                       text='Recommended skills generated from System',
                                                       value=recommended_skills, key='5')
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        rec_course = course_recommender(ios_course)
                        break

                    # UI-UX Recommendation
                    elif skill_lower in uiux_keyword:
                        reco_field = 'UI-UX Development'
                        st.success("** Our analysis says you are looking for UI-UX Development Jobs **")
                        recommended_skills = ['UI', 'User Experience', 'Adobe XD', 'Figma', 'Zeplin', 'Balsamiq',
                                              'Prototyping', 'Wireframes', 'Storyframes', 'Adobe Photoshop', 'Editing',
                                              'Illustrator', 'After Effects', 'Premier Pro', 'Indesign', 'Wireframe',
                                              'Solid', 'Grasp', 'User Research']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                       text='Recommended skills generated from System',
                                                       value=recommended_skills, key='6')
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        rec_course = course_recommender(uiux_course)
                        break

                # Resume score calculation
                st.subheader("**Resume Tips & Ideas💡**")
                resume_score = 0

                if 'Objective' in resume_text:
                    resume_score += 20
                    st.markdown(
                        '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Objective</h4>''',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add your career objective, it will give your career intension to the Recruiters.</h4>''',
                        unsafe_allow_html=True)

                if 'Declaration' in resume_text:
                    resume_score += 20
                    st.markdown(
                        '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Delcaration✍/h4>''',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Declaration✍. It will give the assurance that everything written on your resume is true and fully acknowledged by you</h4>''',
                        unsafe_allow_html=True)

                if 'Hobbies' in resume_text or 'Interests' in resume_text:
                    resume_score += 20
                    st.markdown(
                        '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Hobbies⚽</h4>''',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Hobbies⚽. It will show your persnality to the Recruiters and give the assurance that you are fit for this role or not.</h4>''',
                        unsafe_allow_html=True)

                if 'Achievements' in resume_text:
                    resume_score += 20
                    st.markdown(
                        '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Achievements🏅 </h4>''',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Achievements🏅. It will show that you are capable for the required position.</h4>''',
                        unsafe_allow_html=True)

                if 'Projects' in resume_text:
                    resume_score += 20
                    st.markdown(
                        '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects👨‍💻 </h4>''',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Projects👨‍💻. It will show that you have done work related the required position or not.</h4>''',
                        unsafe_allow_html=True)

                # Resume Score Progress Bar
                st.subheader("**Resume Score📝**")
                st.markdown(
                    """
                    <style>
                        .stProgress > div > div > div > div {
                            background-color: #d73b5c;
                        }
                    </style>""",
                    unsafe_allow_html=True,
                )
                my_bar = st.progress(0)
                score = 0
                for percent_complete in range(resume_score):
                    score += 1
                    time.sleep(0.1)
                    my_bar.progress(percent_complete + 1)

                st.success('** Your Resume Writing Score: ' + str(score) + '**')
                st.warning(
                    "** Note: This score is calculated based on the content that you have added in your Resume. **")
                st.balloons()

                # Insert data to database
                if connection and cursor:
                    ts = time.time()
                    cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                    cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    timestamp = str(cur_date + '_' + cur_time)

                    insert_data(
                        resume_data['name'],
                        resume_data['email'],
                        str(resume_score),
                        timestamp,
                        str(resume_data['no_of_pages']),
                        reco_field,
                        cand_level,
                        str(resume_data['skills']),
                        str(recommended_skills),
                        str(rec_course)
                    )

                # Display example video recommendations (without using pafy)
                st.header("**Bonus Video for Resume Writing Tips💡**")
                resume_vid = random.choice(resume_videos)
                vid_title = fetch_yt_title(resume_vid)
                st.subheader("✅ **" + vid_title + "**")
                st.video(resume_vid)

                st.header("**Bonus Video for Interview👨‍💼 Tips💡**")
                interview_vid = random.choice(interview_videos)
                int_vid_title = fetch_yt_title(interview_vid)
                st.subheader("✅ **" + int_vid_title + "**")
                st.video(interview_vid)

                if connection:
                    connection.commit()
            else:
                st.error('Something went wrong with resume parsing...')
    else:
        # Admin Side
        st.success('Welcome to Admin Side')

        ad_user = st.text_input("Username")
        ad_password = st.text_input("Password", type='password')

        if st.button('Login'):
            if ad_user == 'machine_learning_hub' and ad_password == 'mlhub123':
                st.success("Welcome Kushal")

                # Display Data if database connection exists
                if connection and cursor:
                    cursor.execute('''SELECT * FROM user_data''')
                    data = cursor.fetchall()

                    st.header("**User's👨‍💻 Data**")
                    df = pd.DataFrame(data, columns=['ID', 'Name', 'Email', 'Resume Score', 'Timestamp', 'Total Page',
                                                     'Predicted Field', 'User Level', 'Actual Skills',
                                                     'Recommended Skills',
                                                     'Recommended Course'])
                    st.dataframe(df)
                    st.markdown(get_table_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)

                    # Pie chart for predicted field recommendations
                    labels = df.iloc[:, 6].unique()  # Predicted Field column
                    values = df.iloc[:, 6].value_counts()
                    st.subheader("📈 **Pie-Chart for Predicted Field Recommendations**")
                    fig = px.pie(df, values=values, names=labels, title='Predicted Field according to the Skills')
                    st.plotly_chart(fig)

                    # Pie chart for User's👨‍💻 Experienced Level
                    labels = df.iloc[:, 7].unique()  # User Level column
                    values = df.iloc[:, 7].value_counts()
                    st.subheader("📈 ** Pie-Chart for User's👨‍💻 Experienced Level**")
                    fig = px.pie(df, values=values, names=labels, title="Pie-Chart📈 for User's👨‍💻 Experienced Level")
                    st.plotly_chart(fig)
                else:
                    st.error("Database connection failed. Cannot display admin analytics.")
            else:
                st.error("Wrong ID & Password Provided")


# Run the main application
if __name__ == "__main__":
    run()