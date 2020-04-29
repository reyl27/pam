from .core import Population, Household, Person
from .activity import Plan, Activity, Leg
from .utils import minutes_to_datetime as mtdt

import random


class Policy:

    def __init__(self):
        self.population = Population

    def apply_to(self, household):
        raise NotImplementedError


class HouseholdQuarantined(Policy):
    """
    Probabilistic everyone in household stays home

    by default, person_based=False: Probability household-based,
    i.e. the probability of a household being quarantined

    person_based=True: Probability person-based,
    i.e. the probability of any person in the household
    needing to be quarantined
    """

    def __init__(self, probability, person_based=False):
        super().__init__()

        assert 0 < probability <= 1
        self.probability = probability
        self.person_based = person_based

    def apply_to(self, household):
        if self.person_based:
            p = (1 - (1 - self.probability) ** len(household.people))
        else:
            p = self.probability
        if random.random() < p:
            for pid, person in household.people.items():
                person.stay_at_home()


class PersonStayAtHome(Policy):
    """
    Probabilistic person stays home
    """

    def __init__(self, probability):
        super().__init__()

        assert 0 < probability <= 1
        self.probability = probability

    def apply_to(self, household):
        for pid, person in household.people.items():
            if random.random() < self.probability:
                person.stay_at_home()


class RemoveActivity(Policy):
    """
    Probabilistic remove activities

    :param activities: list of activities to be removed from persons plans
    :param probability: value > 0 and <= 1, likelihood of activities
    having to be removed
    :param probability_level: the level at which the probability should
    be applied.
    e.g. if your `probability` value refers to how likely an
    individual activity is to be removed probability_level = 'activity'
    e.g. if your `probability` value refers to how likely a
    person is affected and their activity to be removed as a
    consequence probability_level = 'person'
    e.g. if your `probability` value refers to how likely a
    household is affected and the persons in that household
    to have activity be removed as a consequence
    probability_level = 'household'
    :param policy_type: policy type, the level at which it should be applied
    policy_type = 'activity'

    policy_type = 'person'

    policy_type = 'household'

    :param attribute_conditions: dictionary of the form {'attribute_key': attribute_condition},
    where attribute_condition is a function returning a boolean:
    def attribute_condition(attribute_value):
        return boolean
    e.g.
    def age_condition_over_17(attribute_value):
        return attribute_value > 17
    and
    attribute_conditions = {'age': age_condition_over_17}

    :param attribute_strict_conditions how to satisfy the attribute_conditions
    attribute_strict_conditions = True: person needs to satisfy
    all conditions in attribute_conditions
    attribute_strict_conditions = False: person needs to satisfy
    just one condition in attribute_conditions
    """

    def __init__(self, activities: list, probability,
                probability_level='activity', policy_type='activity',
                 attribute_conditions=None, attribute_strict_conditions=True):
        super().__init__()

        self.activities = activities
        assert 0 < probability <= 1
        self.probability = probability
        assert probability_level in ['activity', 'person', 'household']
        self.probability_level = probability_level
        assert policy_type in ['activity', 'person', 'household']
        self.policy_type = policy_type
        assert attribute_conditions != {}, 'attribute_conditions cannot be empty'
        if attribute_conditions is not None:
            assert isinstance(attribute_conditions, dict)
        self.attribute_conditions = attribute_conditions
        assert isinstance(attribute_strict_conditions, bool)
        self.attribute_strict_conditions = attribute_strict_conditions

    def apply_to(self, household):
        if self.policy_type == 'household':
            self.evaluate_household_policy(household)
        elif self.policy_type == 'person':
            self.evaluate_person_policy(household)
        else:
            self.evaluate_activity_policy(household)

    def evaluate_activity_policy(self, household):
        if self.probability_level == 'activity':
            for pid, person in household.people.items():
                if self.person_satisfies_attribute_conditions(person):
                    self.remove_individual_activities(person)
        else:
            raise NotImplementedError

    def evaluate_person_policy(self, household):
        if self.probability_level == 'person':
            for pid, person in household.people.items():
                if self.person_is_selected(person):
                    self.remove_person_activities(person)
        elif self.probability_level == 'activity':
            for pid, person in household.people.items():
                if self.person_satisfies_attribute_conditions(person):
                    for activity in person.activities:
                        if self.is_activity_for_removal(activity) and self.is_selected():
                            self.remove_person_activities(person)
        else:
            raise NotImplementedError

    def evaluate_household_policy(self, household):
        if self.probability_level == 'household':
            if self.household_is_selected:
                self.remove_household_activities(household)
        elif self.probability_level == 'person':
            for pid, person in household.people.items():
                if self.person_satisfies_attribute_conditions(person) and self.person_is_selected(person):
                        self.remove_household_activities(household)
        else:
            for pid, person in household.people.items():
                if self.person_satisfies_attribute_conditions(person):
                    for activity in person.activities:
                        if self.is_activity_for_removal(activity) and self.is_selected():
                            self.remove_household_activities(household)

    def remove_activities(self, person, p):
        seq = 0
        while seq < len(person.plan):
            act = person.plan[seq]
            if self.is_activity_for_removal(act) and p():
                previous_idx, subsequent_idx = person.remove_activity(seq)
                person.fill_plan(previous_idx, subsequent_idx, default='home')
            else:
                seq += 1

    def remove_individual_activities(self, person):
        self.remove_activities(person, p=self.is_selected)

    def remove_person_activities(self, person):
        def return_true():
            return True
        self.remove_activities(person, p=return_true)

    def remove_household_activities(self, household):
        for pid, person in household.people.items():
            self.remove_person_activities(person)

    def person_is_selected(self, person):
        if self.is_selected():
            if self.person_satisfies_attribute_conditions(person):
                return True
        return False

    def household_is_selected(self, household):
        if self.is_selected():
            for pid, person in household.people.items():
                if self.person_satisfies_attribute_conditions(person):
                    # if just one of the people satisfies the attributes
                    return True
        return False

    def is_selected(self):
        return random.random() < self.probability

    def is_activity_for_removal(self, p):
        return p.act.lower() in self.activities

    def person_satisfies_attribute_conditions(self, person):
        if self.attribute_conditions is not None:
            if self.attribute_strict_conditions:
                satisfies_attribute_conditions = True
                for attribute_key, attribute_condition in self.attribute_conditions.items():
                    satisfies_attribute_conditions &= attribute_condition(person.attributes[attribute_key])
            else:
                satisfies_attribute_conditions = False
                for attribute_key, attribute_condition in self.attribute_conditions.items():
                    satisfies_attribute_conditions |= attribute_condition(person.attributes[attribute_key])
            return satisfies_attribute_conditions
        else:
            return True


def apply_policies(population: Population, policies: list):

    """
    Apply policies to modify population.
    :param population:
    :param policies:
    :return:
    """

    for hid, household in population.households.items():
        for policy in policies:
            policy.apply_to(household)

