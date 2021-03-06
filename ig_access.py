"""
Module for IG Access
"""
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import time


class IGAccessException(Exception):
    """Handle IGAccess Exceptions"""
    pass


class IGAccess:
    """
    Class used to access data from Instagram using Selenium

    === Attributes ===
    logged_in     - whether or not user is logged in
    show_progress - whether or not to print progress to user
    driver        - selenium webdriver object
    followers     - list of followers
    following     - list of following
    data          - dictionary of collected data, keys are usernames with a value of dictionary with keys:
                    > num_followers
                    > num_following
                    > followers
                    > following
                    > not_followed_back
                    > not_following_back
                    > following_verified
                    > followed_by_verified
                    > num_posts
                    > data_per_post - list of dictionaries for each post, keys:
                        > id
                        > likes
                        > liked_by
                        > comments
                    > total_likes
                    > avg_likes
    """
    show_progress: bool
    chromedriver_location: str

    def __init__(self, chromedriver_location: str, show_progress: bool) -> None:
        """
        Initialize a new IG Check class
        """
        self.show_progress = show_progress
        self.logged_in = False
        self.data = {}

        if chromedriver_location == '':  # User put chromedriver.exe into PATH.
            self.driver = webdriver.Chrome()
        else:
            self.driver = webdriver.Chrome(chromedriver_location)

    # ===== SETUP/TEARDOWN METHODS =====

    def login(self, username, password) -> None:
        """
        Log into Instagram
        """
        if self.show_progress:
            print('Logging in')

        self.driver.get('https://www.instagram.com/accounts/login/')

        time.sleep(1)

        self.driver.find_element_by_name('username').send_keys(username)
        self.driver.find_element_by_name('password').send_keys(password)

        waiting_animation = ['\\', '|', '/', '-']

        # Prompt user to click 'Log in' button
        print('PROMPT: Click \'Log in\' -', end='')

        animation_index = 0
        # Loop until user clicks 'Log in'
        while not self.logged_in:
            try:
                # Check if password was incorrect, if so, raise an exception, otherwise ignore it
                try:
                    self.driver.find_element_by_id('slfErrorAlert')
                    print('\n')
                    raise IGAccessException('Incorrect password, double-check the username and password you provided')
                except NoSuchElementException:
                    pass

                # Check if 'profile' icon is showing on page (implies login was successful)
                self.driver.find_element_by_class_name('coreSpriteDesktopNavProfile')
                self.logged_in = True
                print('\rPROMPT: Click \'Log in\' :)')
            except NoSuchElementException:
                print('\rPROMPT: Click \'Log in\' %s' % waiting_animation[animation_index % 4], end='', flush=True)
                animation_index += 1
                time.sleep(1)

    def logout(self, username) -> None:
        """
        Logout of Instagram and exit
        """
        if self.show_progress:
            print('\nLogging out')

        # Go to user's profile
        self.driver.get('https://www.instagram.com/%s' % username)

        # Scroll to the top and click settings
        self.driver.execute_script("window.scrollBy(0, -document.body.scrollHeight);")
        self.driver.find_element_by_class_name('coreSpriteMobileNavSettings').click()

        # Click logout
        self.driver.find_element_by_xpath('/html/body/div[4]/div/div[2]/div/ul/li[4]').click()

        self.logged_in = False

    def tear_down(self) -> None:
        """
        Close driver
        """
        self.driver.close()

    # ===== DATA-RETURNING METHODS =====

    def is_account(self, username: str) -> bool:
        """
        Return whether username is associated with an Instagram account
        """
        self.driver.get('https://www.instagram.com/%s' % username)

        time.sleep(1)

        # Try to find an error msg
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_error_msg = soup.find_all('div', {'class': '-cx-PRIVATE-ErrorPage__errorContainer'})

        return not (page_error_msg != [] and
                    page_error_msg[0].find('h2').get_text() == 'Sorry, this page isn\'t available.')

    def is_private(self, username: str) -> bool:
        """
        Return whether username's account is private on Instagram
        """

        self.driver.get('https://www.instagram.com/%s' % username)

        time.sleep(1)

        # Try to find 'Account is private' msg
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        private_data = soup.find_all('h2', {'class': '_kcrwx'})

        return not (private_data != [] and
                    private_data[0].get_text() == 'This Account is Private')

    # ===== DATA-HANDLING METHODS =====

    def collect_follow_data(self, username: str) -> None:
        """
        Collect data about user's followers and following
        """
        if self.show_progress:
            print('Getting user\'s followers')
        # Get list of user's followers
        self.driver.get('https://www.instagram.com/%s' % username)
        self.driver.execute_script("window.scrollBy(0, -document.body.scrollHeight);")
        followers = self._get_followers()

        if self.show_progress:
            print('Getting user\'s following')
        # Get list of users user's following
        self.driver.get('https://www.instagram.com/%s' % username)
        following = self._get_following()

        # Add to self.data
        try:
            self.data[username]
        except KeyError:  # username isn't in self.data yet
            self.data[username] = {}
        self.data[username]['num_followers'] = len(followers)
        self.data[username]['num_following'] = len(following)
        self.data[username]['followers'] = followers
        self.data[username]['following'] = following

    def collect_follow_diff(self) -> None:
        """
        Collect data list about the difference between user's followers and following and append it to self.data
        """
        if self.show_progress:
            print('Analysing follower/following data')

        for username in self.data:

            followers = self.data[username]['followers']
            following = self.data[username]['following']

            not_followed_back = [user for user in following if user not in followers]
            not_following_back = [user for user in followers if user not in following]

            following_verified = [user for user in following if '(Verified)' in user]
            followed_by_verified = [user for user in followers if '(Verified)' in user]

            # Append gathered data into self.data
            self.data[username]['not_followed_back'] = not_followed_back
            self.data[username]['not_following_back'] = not_following_back
            self.data[username]['following_verified'] = following_verified
            self.data[username]['followed_by_verified'] = followed_by_verified

    def collect_posts_data(self, username: str) -> None:
        """
        Collect like and comment data on user's posts
        """
        self.driver.get('https://www.instagram.com/%s' % username)

        if self.show_progress:
            print('Getting data per post')

        soup = BeautifulSoup(self.driver.page_source, 'html.parser')

        # Get total number of posts
        num_of_posts = int(soup.html.body.span.section.main.article.find_all('span', {'class': '_fd86t'})[0]
                           .get_text().replace(',', ''))

        # Get post id's and add dictionaries with this data to data_per_post
        data_per_post = []
        for link in soup.html.body.span.section.main.article.findAll('a', href=True):
            if link['href'].startswith('/p/'):
                data_per_post.append({'id': link['href'].split('/')[2]})

        for i in range(num_of_posts):
            post_id = data_per_post[i]['id']

            # Get img based on post_id
            img = self.driver.find_element_by_xpath('//a[contains(@href, "' + post_id + '")]')

            # Hover over image
            ActionChains(self.driver).move_to_element(img).perform()

            # Get comments data and add it to data_per_post
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            comments = soup.find_all('li', {'class': '_3apjk'})[0].getText().split('c')[0]
            data_per_post[i]['comments'] = comments

            # soup can only see 12 additional items at a time, so we need to scroll down and load again when i hits a
            # multiple of 12 minus 1
            if (i + 1) % 12 == 0:
                # Scroll down
                self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')

                time.sleep(1)

                # Get refreshed page_source
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')

                for link in soup.html.body.span.section.main.article.find_all('a', href=True):
                    if link['href'].startswith('/p/'):
                        new_id = link['href'].split('/')[2]
                        # Add new_id iff it's not already in data_per_post
                        if new_id not in [dict_['id'] for dict_ in data_per_post]:
                            data_per_post.append({'id': new_id})

        # Get like data
        self._get_like_data(num_of_posts, data_per_post)

        # Calculate total_likes and avg_likes
        total_likes = sum([data['likes'] for data in data_per_post])

        avg_likes = 0
        if len(data_per_post) != 0:
            avg_likes = total_likes / len(data_per_post)

        # Add collected data to self attribute
        try:
            self.data[username]
        except KeyError:  # username isn't in self.data yet
            self.data[username] = {}
        self.data[username]['data_per_post'] = data_per_post
        self.data[username]['total_likes'] = total_likes
        self.data[username]['avg_likes'] = avg_likes

    def output_data(self) -> None:
        """
        Output self.data to analytic_data.json
        Updates data if already present.
        """
        import os
        import json
        from json.decoder import JSONDecodeError

        if self.show_progress:
            print('\nWriting data to analytic_data.json')

        # If file doesn't exist already, create it
        if not os.path.isfile('analytic_data.json'):
            data = {}
            with open('analytic_data.json', 'w+') as f:
                json.dump(data, f, indent=4)
        else:  # Otherwise read from file
            with open('analytic_data.json', 'r') as f:
                try:
                    data = json.load(f)
                except JSONDecodeError:  # file is empty
                    data = {}

        # Update data dict and add it to file
        with open('analytic_data.json', 'w') as f:
            for user in self.data:
                data[user] = self.data[user]

            json.dump(data, f, indent=4)

    # ===== PRIVATE HELPER METHODS =====

    def _get_followers(self) -> List[str]:
        """
        Return a list of user's followers
        """
        # Get number of followers and click followers link
        try:
            followers_link = self.driver.find_element_by_xpath(
                '//*[@id="react-root"]/section/main/article/header/section/ul/li[2]/a/span')
            num_of_followers = int(followers_link.get_attribute('title'))
            followers_link.click()
        except NoSuchElementException:  # user has no followers
            return []

        time.sleep(1)

        return self._get_list_of_users(num_of_followers)

    def _get_following(self) -> List[str]:
        """
        Return a list of users user is following
        """
        # Get number of following and click following link
        try:
            following_link = self.driver.find_element_by_xpath(
                '//*[@id="react-root"]/section/main/article/header/section/ul/li[3]/a/span')
            num_following = int(following_link.text.split(' ')[0])
            following_link.click()
        except NoSuchElementException:  # user has no following
            return []

        time.sleep(1)

        return self._get_list_of_users(num_following)

    def _get_list_of_users(self, num_users: int) -> List[str]:
        """
        Return a list of users with len(num_users) from the current iframe window for followers and following
        """
        # Find the current iframe
        dialog = self.driver.find_element_by_xpath('/html/body/div[4]/div/div[2]/div/div[2]')

        if self.show_progress:
            print('\t[' + (' ' * 40) + ']' + ' 0%', end='', flush=True)

        # Keep scrolling down the iframe until all users are showing
        list_of_users = self._clean_list(self.driver.find_element_by_class_name('_b9n99').text)
        while len(list_of_users) < num_users:
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
            list_of_users = self._clean_list(self.driver.find_element_by_class_name('_b9n99').text)

            if self.show_progress:
                percent_comp = len(list_of_users) / num_users
                fill_bar = round(40 * percent_comp)
                print('\r\t[' + ('#' * fill_bar) + (' ' * (40 - fill_bar)) + '] ' +
                      str(round(percent_comp * 100, 3)) + '%', end='', flush=True)

            time.sleep(0.5)

        print('\n')

        return list_of_users

    def _get_like_data(self, num_of_posts: int, data_per_post: List[Dict[str, Any]]) -> None:
        """
        Add data about likes and like_by to data_per_post for each post
        """
        try:
            # Click the first image
            self.driver.find_element_by_xpath('//a[contains(@href, "' + data_per_post[0]['id'] + '")]').click()
        except IndexError:  # user has no posts
            pass

        # Keep hitting next button and gathering data about each post's likes
        for i in range(len(data_per_post)):
            time.sleep(1)
            # Get users who liked post
            users_who_liked = self._get_likes_from_post(i, num_of_posts)

            # Add data to data_per_post
            data_per_post[i]['likes'] = len(users_who_liked)
            data_per_post[i]['liked_by'] = users_who_liked

            try:
                self.driver.find_element_by_class_name('coreSpriteRightPaginationArrow').click()
            except NoSuchElementException:  # Last post encountered
                continue

    def _get_likes_from_post(self, i: int, num_of_posts: int):
        """
        Get number of likes and user who likes post from current iframe
        """
        # Scroll to top
        self.driver.execute_script("window.scrollBy(0, -document.body.scrollHeight);")

        # Get the number of likes and click on the likes link
        like_obj = self.driver.find_element_by_xpath(
            '/html/body/div[4]/div/div[2]/div/article/div[2]/section[2]/div/a')
        num_of_likes = int(like_obj.text.split(' ')[0])
        like_obj.click()

        time.sleep(0.5)

        # Keep scrolling down the iframe until all users are showing
        dialog = self.driver.find_element_by_xpath('/html/body/div[4]/div/div[2]/div/article/div[2]/div[2]')
        list_of_users = self._clean_list(self.driver.find_element_by_class_name('_b9n99').text)

        update_delay = 0  # Keep track of how long it takes to update list

        while len(list_of_users) < num_of_likes:
            last_count = len(list_of_users)  # Keep track of whether list was updated

            # Scroll and get updated list_of_users
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
            list_of_users = self._clean_list(self.driver.find_element_by_class_name('_b9n99').text)

            if self.show_progress:
                percent_comp = i / num_of_posts
                percent_comp += (len(list_of_users) / num_of_likes) / num_of_posts
                fill_bar = round(40 * percent_comp)
                print('\r\t[' + ('#' * fill_bar) + (' ' * (40 - fill_bar)) + '] ' +
                      str(round(percent_comp * 100, 3)) + '%', end='', flush=True)

            time.sleep(0.5)

            if len(list_of_users) == last_count:
                update_delay += 0.5  # list hasn't been updated in ~ 0.5 seconds
            else:
                update_delay = 0

            if update_delay == 5:  # list hasn't been updated for > 5 seconds
                if not len(list_of_users) + 1 == num_of_likes:  # Sometimes the like count is off by 1
                    print('\n')
                    raise IGAccessException(
                        'TIMEOUT ERROR: Page hasn\'t refreshed for 5 seconds, loop stopped at getting user %d of %d'
                        ', try again when you have better internet speeds' % (last_count, num_of_likes))
                elif self.show_progress:
                    percent_comp = (i + 1) / num_of_posts
                    fill_bar = round(40 * percent_comp)
                    print('\r\t[' + ('#' * fill_bar) + (' ' * (40 - fill_bar)) + '] ' +
                          str(round(percent_comp * 100, 3)) + '%', end='', flush=True)
                break

        return list_of_users

    @staticmethod
    def _clean_list(raw_string: str) -> List[str]:
        """
        Returns a list of cleaned followers from list of followers and junk
        """
        return_list = []
        raw_list = raw_string.split('\n')

        # Loop through raw list of users and pick out users
        for i in range(len(raw_list)):
            # If the line is followed by a line containing Following or Follow, it's a username line
            if i == 0 or raw_list[i-1] in ['Following', 'Follow']:
                name = raw_list[i]
                # Add a (Verified) tag if the account is verified
                try:
                    if raw_list[i+1] == 'Verified':
                        name += ' (Verified)'
                except IndexError:  # Internet is slow and page isn't loading fully
                    pass
                return_list.append(name)

        return return_list
