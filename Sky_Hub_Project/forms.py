from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FileField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, URL, Regexp
from flask_wtf.file import FileAllowed

def strip_filter(x):
    return x.strip() if x else None

class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=50)], filters=[strip_filter])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)], filters=[strip_filter])
    
    track = SelectField("Track", choices=[
        ("", "Select Your Track"),
        ("Web Development", "Web Development"),
        ("Mobile App", "Mobile App"),
        ("Data Science", "Data Science"),
        ("AI & Machine Learning", "AI & Machine Learning"),
        ("Cybersecurity", "Cybersecurity"),
        ("Game Development", "Game Development"),
        ("Embedded Systems", "Embedded Systems"),
        ("Other", "Other")
    ], validators=[DataRequired()])
    
    skills = StringField("Top Skills (comma separated)", validators=[DataRequired(), Length(max=200)], filters=[strip_filter])
    available_for_project = BooleanField("Available for Graduation Project?", default=True)

    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")])
    profile_image = FileField("Profile Picture", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png"], "Images only!")])
    cv_file = FileField("Upload Resume (PDF)", validators=[Optional(), FileAllowed(["pdf"], "PDF files only!")])
    submit = SubmitField("Create Account")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)], filters=[strip_filter])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class EditProfileForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=50)], filters=[strip_filter])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)], filters=[strip_filter])
    
    track = SelectField("Track", choices=[
        ("Web Development", "Web Development"),
        ("Mobile App", "Mobile App"),
        ("Data Science", "Data Science"),
        ("AI & Machine Learning", "AI & Machine Learning"),
        ("Cybersecurity", "Cybersecurity"),
        ("Game Development", "Game Development"),
        ("Embedded Systems", "Embedded Systems"),
        ("Other", "Other")
    ], validators=[DataRequired()])
    
    skills = StringField("Top Skills (comma separated)", validators=[DataRequired(), Length(max=200)], filters=[strip_filter])
    available_for_project = BooleanField("Available for Project")
    
    github_link = StringField("GitHub URL", validators=[Optional(), URL()], filters=[strip_filter])
    portfolio_link = StringField("Portfolio URL", validators=[Optional(), URL()], filters=[strip_filter])
    linkedin_link = StringField("LinkedIn URL", validators=[Optional(), URL()], filters=[strip_filter])
    phone_number = StringField("Contact Number", validators=[Optional(), Length(min=7, max=20)], filters=[strip_filter])
    profile_image = FileField("Update Profile Picture", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png"], "Images only!")])
    cv_file = FileField("Update Resume (PDF)", validators=[Optional(), FileAllowed(["pdf"], "PDF files only!")])
    
    submit = SubmitField("Save Professional Profile")

class PostForm(FlaskForm):
    # Title is optional — auto-generated from content snippet in the route
    title = StringField("Title", validators=[Optional(), Length(max=200)], filters=[strip_filter])
    content = TextAreaField("Content", validators=[DataRequired(), Length(min=1)], filters=[strip_filter])
    image = FileField("Upload Image", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "gif"], "Images only!")])
    video = FileField("Upload Video", validators=[Optional(), FileAllowed(["mp4", "webm", "ogg"], "Videos only!")])
    submit = SubmitField("Publish")


class CommentForm(FlaskForm):
    content = TextAreaField("Comment", validators=[DataRequired(), Length(min=1, max=2000)], filters=[strip_filter])
    submit = SubmitField("Post Comment")

class LikeForm(FlaskForm):
    submit = SubmitField("Like")

class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")
