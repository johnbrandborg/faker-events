"""
Profile creation to be used by the Profiler functions passed onto the Event
objects.
"""

import json
from random import choice
from types import SimpleNamespace

from faker import Faker
from .text_color import eprint, Palatte


class ProfileGenerator():
    def __init__(self, fake: Faker = Faker()):
        """
        The Profile Generator instances are used by the Event Generator for
        access to profiles information, used within the Events.

        Parameters
        ----------
            fake: Faker
                A custom instances of Faker that will be used for profile
                generation.
        """
        self.fake = fake
        self.entries = []

    def load(self,
             num_profiles: int = 1,
             profiles_file: str = None) -> None:
        """
        Used to Create, Load, and Save profiles.

        Parameters
        ----------
            num_profiles: int
                The number of profiles to load in the entries list.
            profiles_file: str
                Creates and Uses a file for persistant profiles
        """

        if isinstance(profiles_file, str):
            try:
                with open(profiles_file, encoding="utf-8") as file:
                    profiles_dicts = json.loads(file.read())
                    self.entries = [
                        SimpleNamespace(**profiles)
                        for index, profiles in enumerate(profiles_dicts)
                        if index < num_profiles
                    ]
            except FileNotFoundError:
                eprint(f"No profiles file {profiles_file} found. Creating "
                       "the file now.", Palatte.BLUE)
                self.create(num_profiles)
                self.save(profiles_file)
            if num_profiles > len(self.entries):
                eprint("WARNING: The number of profiles requested, '{}', "
                       "exceeds the profiles file. Consider recreating and "
                       "writing the profiles again.".format(num_profiles),
                       Palatte.YELLOW)
        else:
            self.create(num_profiles)

    def create(self, num_profiles: int) -> None:
        """
        Creates the fake profiles that will be used for event creation, and
        adds them to the entries list.
        """

        fake = self.fake

        for identification in range(num_profiles):
            gender = choice(('male', 'female'))

            if gender == 'female':
                first_name = fake.first_name_female()
                middle_name = fake.first_name_female()
                prefix_name = fake.prefix_female()
                suffix_name = fake.suffix_female()
            else:
                first_name = fake.first_name_male()
                middle_name = fake.first_name_male()
                prefix_name = fake.prefix_male()
                suffix_name = fake.suffix_male()

            last_name = fake.last_name()
            address = '{{building_number}}|{{street_name}}|{{state_abbr}}' \
                      '|{{postcode}}|{{city}}'
            address1 = fake.parse(address).split('|')
            profile = {
                'id': str(identification + 1000),
                'uuid': fake.uuid4(),
                'username': fake.user_name(),
                'gender': gender,
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
                'prefix_name': prefix_name,
                'suffix_name': suffix_name,
                'birthdate': fake.date_of_birth(minimum_age=18,
                                                maximum_age=80)
                            .isoformat(),
                'blood_group': (choice(["A", "B", "AB", "O"]) +
                                choice(["+", "-"])),
                'email': f'{first_name}.{last_name}@{fake.domain_name()}',
                'employer': fake.company(),
                'job': fake.job(),
                'full_address1': ' '.join(address1),
                'building_number1': address1[0],
                'street_name1': address1[1].split(' ')[0],
                'street_suffix1': address1[1].split(' ')[1],
                'state1': address1[2],
                'postcode1': address1[3],
                'city1': address1[4],
                'phone1': fake.phone_number(),
                'full_address2': ' '.join(address1),
                'building_number2': address1[0],
                'street_name2': address1[1].split(' ')[0],
                'street_suffix2': address1[1].split(' ')[1],
                'state2': address1[2],
                'postcode2': address1[3],
                'city2': address1[4],
                'phone2': fake.phone_number(),
                'driver_license': fake.bothify('?#####'),
                'license_plate': fake.license_plate(),
            }

            self.entries.append(SimpleNamespace(**profile))

    def save(self, profiles_file: str) -> None:
        """
        Saves the profile entries created to a JSON file.
        """

        with open(profiles_file, 'w', encoding="utf-8") as file:
            profiles_dicts = [vars(item) for item in self.entries]
            file.write(json.dumps(profiles_dicts))
