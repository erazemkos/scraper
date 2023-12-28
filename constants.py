class KEYS:
    URL = 'Url'
    TITLE = 'Title'
    SUMMARY = 'Summary'
    DATETIME = "DateTime"
    TEXT = 'FullText'
    PRIORITY = 'PRIORITY'

    @staticmethod
    def get_all_keys():
        return [KEYS.URL, KEYS.TITLE, KEYS.SUMMARY, KEYS.DATETIME, KEYS.TEXT, KEYS.PRIORITY]


class SupportedSites:
    RTVSLO = 'rtvslo'

    @staticmethod
    def all():
        return tuple(SupportedSites.RTVSLO)
