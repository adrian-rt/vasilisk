import redis

from collections import Counter

from .group import Group
from .group import string_to_group


class CoverageHandler(object):
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0,
                                 decode_responses=True)

        self.redis.set('generated', 0)
        self.redis.set('processed', 0)

    def reset(self):
        self.redis.set('generated', 0)
        self.redis.set('processed', 0)

        scores = Counter()
        for id in self.redis.lrange('finals', 0, -1):
            scores[id] = self.redis.get(f'score:{id}')

        for id, score in scores.most_common(10):
            group_string = self.redis.get(f'group:{id}')
            group = string_to_group(group_string)
            self.redis.set(f'interesting:{group.store()}', score)

    def up_to_date(self):
        if self.redis.get('generated') == self.redis.get('processed'):
            return True
        return False

    def store(self, id, actions_to_variables, resolved_variables,
              controls, interactions, final=False):
        self.redis.incr('generated')
        if final:
            group = Group(actions_to_variables, resolved_variables,
                          controls, interactions)
            self.redis.lpush('finals', id)
            self.redis.set(f'group:{id}', group.to_string())