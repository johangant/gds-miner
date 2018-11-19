import scrapy
import json
import requests
from html_sanitizer import Sanitizer

class GdsMiner(scrapy.Spider):
    name = 'gdsminer'
    start_urls = ['https://www.digitalmarketplace.service.gov.uk/digital-outcomes-and-specialists/opportunities?q=&lot=digital-outcomes&statusOpenClosed=open']
    opportunities = []

    def parse(self, response):
        results = []

        for item in response.css('#js-dm-live-search-results .search-result'):
            title = item.css('.search-result-title a::text').extract()
            page_url = item.css('.search-result-title a::attr(href)').extract_first().strip()

            results.append({
                'title': title,
                'page_url': page_url,
            })

        for item in results:
            opportunity_url = item['page_url']
            if opportunity_url is not None:
                yield response.follow(opportunity_url, callback=self.parse_opportunity)

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
        webhook_url = 'https://hooks.zapier.com/hooks/catch/4077741/ejn6bw/'

        response = requests.post(
            webhook_url, data=json.dumps(opportunity),
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code != 200:
            raise ValueError(
                'Request returned an error %s, the response is:\n%s'
                % (response.status_code, response.text)
            )