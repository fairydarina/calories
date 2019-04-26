import pygame
import requests
import sys
import os

import math

from distance import lonlat_distance
from geo import reverse_geocode
from bis import find_business


LAT_STEP = 0.0016
LON_STEP = 0.0016
coord_to_geo_x = 0.0000428
coord_to_geo_y = 0.0000428

lst = []

def ll(x, y):
    return '{0},{1}'.format(x, y)


class SearchResult(object):
    def __init__(self, point, address, postal_code=None):
        self.point = point
        self.address = address
        self.postal_code = postal_code
        

class MapParams(object):
    def __init__(self):
        self.lat = 55.729738
        self.lon = 37.664777
        self.zoom = 15
        self.type = 'map'
        self.search_result = None
        self.use_postal_code = False

        
    def ll(self):
        return ll(self.lon, self.lat)
    
    def update(self, event):
        if event.key == 280 and self.zoom < 19:
            lst.clear()
            self.zoom += 1
        elif event.key == 281 and self.zoom > 2:
            lst.clear()
            self.zoom -= 1
        elif event.key == 276:
            lst.clear()
            self.lon -= LON_STEP * math.pow(2, 15 - self.zoom)
        elif event.key == 275:
            lst.clear()
            self.lon += LON_STEP * math.pow(2, 15 - self.zoom)
        elif event.key == 273 and self.lat < 85:
            lst.clear()
            self.lat += LAT_STEP * math.pow(2, 15 - self.zoom)
        elif event.key == 274 and self.lat > -85:
            lst.clear()
            self.lat -= LAT_STEP * math.pow(2, 15 - self.zoom)
        elif event.key == 49:
            self.type = 'map'
        elif event.key == 50:
            self.type = 'sat'
        elif event.key == 51:
            self.type = 'sat,skl'
        elif event.key == 127:
            self.search_result = None
        elif event.key == 277:
            self.use_postal_code = not self.use_postal_code
            
        if self.lon > 180: self.lon -= 360
        if self.lon < -180: self.lon += 360
        
    def screen_to_geo(self, pos):
        dy = 225 - pos[1]
        dx = pos[0] - 300
        lx = self.lon + dx * coord_to_geo_x * math.pow(2, 15 - self.zoom)
        ly = self.lon + dy * coord_to_geo_y * math.cos(math.radians(self.lat)) 
        return lx, ly
    
    def add_reverse_toponym_search(self, pos):
        point = self.screen_to_geo(pos)
        toponym = reverse_geocode(ll(point[0], point[1]))
        self.search_result = SearchResult(
            point,
            toponym['metaDataProperty']['GeocoderMetaData']['text'] if toponym else None,
            toponym['metaDataProperty']['GeocoderMetaData']['Address'].get('postal_code') if toponym else None)
        
    def add_reverse_org_search(self, pos):
        self.search_result = None
        point = self.screen_to_geo(pos)
        org = find_business(ll(point[0], point[1]))
        if not org:
            return
        
        org_point = org['geometry']['coordinates']
        org_lon = float(org_point[0])
        org_lat = float(org_point[1])

        if lonlat_distance((org_lon, org_lat), point) <= 50:
            self.search_result = SearchResult(point, org['properties']['CompanyMetaData']['name'])
            
def load_map(mp):
    map_request = 'http://static-maps.yandex.ru/1.x/?ll={ll}&z={z}&l={type}'.format(ll=mp.ll(), z=mp.zoom, type=mp.type)
    if mp.search_result:
        map_request += '&pt={0},{1},pm2grm'.format(mp.search_result.point[0], mp.search_result.point[1])

    response = requests.get(map_request)
    if not response:
        print('Ошибка выполнения запроса:')
        print(map_request)
        print('Http статус:', response.status_code, '(', response.reason, ')')
        sys.exit(1)
        
    map_file = 'map.png'
    try:
        with open(map_file, 'wb') as file:
            file.write(response.content)
    except IOError as ex:
        print('Ошибки записи временного файла:', ex)
        sys.exit(2)
        
    return map_file

def render_text(text):
    font = pygame.font.Font(None, 30)
    return font.render(text, 1, (255, 0, 0))


def main():
    pygame.init()
    screen = pygame.display.set_mode((600, 450))
    mp = MapParams()
    map_file = load_map(mp)

    while True:
        event = pygame.event.wait()
        if event.type == pygame.QUIT:
            break
        elif event.type == pygame.KEYUP:
            mp.update(event)
            map_file = load_map(mp)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                pos = pygame.mouse.get_pos()
                lst.append(pos)
        
        screen.blit(pygame.image.load(map_file), (0, 0))
        
        if len(lst) > 1:
            pygame.draw.lines(screen, (255,0,0), False, lst, 2)
        
        count = 1
        font = pygame.font.Font(None, 30)
        
        for i in lst:
            pygame.draw.circle(screen, (255,0,0), i, 3, 0)
        
            text = font.render(str(count), 1, (255,0,0))
            screen.blit(text, (int(i[0]) - 15, int(i[1]) - 15))
            count += 1
            
        dist = 0
        if len(lst) > 1:
            for j in range(len(lst) - 1):
                a = mp.screen_to_geo(lst[j])
                b = mp.screen_to_geo(lst[j + 1])
                dist += lonlat_distance(a, b)
        calories = 0
        
        if dist > 0:        
            calories = int(dist * 67.5 / 1000)
        
        dist = int(dist)
        if len(lst) < 2:
            text = render_text('Укажите точки с помощью левой кнопки мыши.')
        else:
            text = render_text('Вы прошли ' + str(dist) + ' м. и потратили ' + str(calories) + ' ккал.')
        screen.blit(text, (0, 430))
        
        if mp.search_result:
            if mp.use_postal_code and mp.search_result.postal_code:
                text = render_text(mp.search_result.postal_code + ', ' + mp.search_result.address)
            else:
                text = render_text(mp.search_result.address)
                
        pygame.display.flip()
    pygame.quit()     
    
if __name__ == '__main__':
    main()