import scrapy

class GdsMiner(scrapy.Spider):
    name = 'gdsminer'
    start_urls = ['https://www.digitalmarketplace.service.gov.uk/digital-outcomes-and-specialists/opportunities?q=&lot=digital-outcomes&statusOpenClosed=open']

    def parse(self, response):
        results = []

        for item in response.css('#js-dm-live-search-results .search-result'):
            title = item.css('.search-result-title a::text').extract()
            page_url = item.css('.search-result-title a::attr(href)').extract_first().strip()
            metadata = []

            for i, mdata in enumerate(item.css('ul.search-result-metadata')):
                metadata.append(mdata.css('li::text').extract_first().strip())

            results.append({
                'title': title,
                'page_url': page_url,
                'metadata': metadata
            })

        for item in results:
            next_page = response.urljoin(item['page_url'])
            yield scrapy.Request(next_page, callback=self.parse)