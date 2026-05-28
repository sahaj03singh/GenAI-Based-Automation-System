class RequirementAgent:

    def read_user_stories(self):

        with open("userstories.txt", "r") as f:
            return f.read()   