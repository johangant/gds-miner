import scrapy
import json
import requests
from simplegist import Simplegist
from html_sanitizer import Sanitizer

class GdsMiner(scrapy.Spider):
    name = 'gdsminer'
    start_urls = ['https://www.digitalmarketplace.service.gov.uk/digital-outcomes-and-specialists/opportunities?q=&lot=digital-outcomes&statusOpenClosed=open']
    gist_id = 'fa6713097f9ab2b9af7c319930c353e3'
    gist_token = 'd12935036b674103da959061889c5247b46b1949'
    ghuser = 'johangant'
    known_opportunities = []
    found_opportunities = []
    new_opportunities = []

    gist = Simplegist(username=ghuser, api_token=gist_token)
    known_opportunities = gist.profile().content(id=gist_id).split()

    def parse(self, response):
        results = []

        for item in response.css('#js-dm-live-search-results .search-result'):
            title = item.css('.search-result-title a::text').extract()
            page_url = item.css('.search-result-title a::attr(href)').extract_first().strip()

            results.append({
                'title': title,
                'page_url': page_url,
            })

        if results is None:
            print "No results found"
            sys.exit(1)

        for item in results:
            opportunity_url = response.urljoin(item['page_url'])
            if opportunity_url is not None:
                # Track all opportunities we pass.
                self.found_opportunities.append(opportunity_url)

                # If it's new, then parse it and handle it accordingly.
                if opportunity_url not in self.known_opportunities:
                    self.new_opportunities.append(opportunity_url)
                    yield response.follow(opportunity_url, callback=self.parse_opportunity)

        if len(self.new_opportunities) > 0:
            # Update the gist with each pass with all opportunities we've found. Better in future to
            # do this at the very end as otherwise we access the GitHub API for every page.
            self.gist.profile().edit(id=self.gist_id, content="\n".join(self.found_opportunities))

        # Jump to next page, if we have one.
        next_page = response.css('ul.previous-next-navigation li.next a::attr(href)').extract_first()
        if next_page is not None:
            next_page = response.urljoin(next_page)
            yield scrapy.Request(next_page, callback=self.parse)

    def parse_opportunity(self, response):
        full_payload = ""
        # Blurt it all out in full for now.
        sanitizer = Sanitizer({
            'tags': ('hr', 'a', 'br', 'p', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'table', 'tbody', 'tr', 'td'),
        })

        matches = response.xpath('.//div[@class="column-one-whole"]').extract()
        for item in matches:
            full_payload = "".join(sanitizer.sanitize(item))

        self.store_opportunity({
            'title': response.css('header h1::text').extract_first().strip(),
            'url': response.request.url,
            'incomplete_applications': response.css('#incomplete-applications .big-statistic::text').extract_first().strip(),
            'complete_applications': response.css('#completed-applications .big-statistic::text').extract_first().strip(),
            'full_text': full_payload,
        })

    def store_opportunity(self, opportunity):
        response = requests.post(
            webhook_url, data=json.dumps(opportunity),
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code != 200:
            raise ValueError(
                'Request returned an error %s, the response is:\n%s'
                % (response.status_code, response.text)
            )