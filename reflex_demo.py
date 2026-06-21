import pygame
import sys
import random

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ani Void Reflex Demo - Travelers Subsystem")
clock = pygame.time.Clock()

BLACK = (0, 0, 0)
PURPLE = (100, 0, 200)
CYAN = (0, 255, 255)
RED = (255, 0, 0)

class AniVoid:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.size = 50
        self.emotion = "neutral"
        self.reflex_timer = 0
        self.pulse = 0  # soul essence flare
    
    def update(self, stimuli):
        if stimuli.get("sudden_noise", False):
            self.emotion = "surprised"
            self.reflex_timer = 30
            self.pulse = 20
        elif stimuli.get("touch", False):
            self.emotion = "happy" if random.random() > 0.5 else "scared"
            self.reflex_timer = 20
        elif stimuli.get("emotional_cue", "neutral") != "neutral":
            self.emotion = stimuli["emotional_cue"]
            self.reflex_timer = 15
        
        if self.reflex_timer > 0:
            self.reflex_timer -= 1
        else:
            self.emotion = "neutral"
        
        self.pulse = max(0, self.pulse - 1)
    
    def draw(self, surface):
        pygame.draw.circle(surface, PURPLE, (self.x, self.y), self.size)  # body
        aura_size = self.size + self.pulse
        pygame.draw.circle(surface, CYAN, (self.x, self.y), aura_size, 5)  # energy aura
        
        # Eyes
        if self.emotion == "surprised":
            pygame.draw.circle(surface, RED, (self.x - 15, self.y - 10), 8)
            pygame.draw.circle(surface, RED, (self.x + 15, self.y - 10), 8)
        elif self.emotion == "happy":
            pygame.draw.ellipse(surface, (0, 255, 100), (self.x - 20, self.y - 15, 15, 10))
            pygame.draw.ellipse(surface, (0, 255, 100), (self.x + 5, self.y - 15, 15, 10))
        elif self.emotion == "scared":
            pygame.draw.circle(surface, RED, (self.x - 15, self.y - 10), 5)
            pygame.draw.circle(surface, RED, (self.x + 15, self.y - 10), 5)
        else:
            pygame.draw.circle(surface, CYAN, (self.x - 15, self.y - 10), 6)
            pygame.draw.circle(surface, CYAN, (self.x + 15, self.y - 10), 6)
        
        # Mouth
        if self.emotion == "happy":
            pygame.draw.arc(surface, (255, 255, 255), (self.x - 20, self.y + 5, 40, 20), 0, 3.14, 3)
        elif self.emotion in ["surprised", "scared"]:
            pygame.draw.line(surface, (255, 255, 255), (self.x - 15, self.y + 15), (self.x + 15, self.y + 15), 3)
        else:
            pygame.draw.line(surface, (255, 255, 255), (self.x - 15, self.y + 10), (self.x + 15, self.y + 10), 3)

def main():
    ani = AniVoid()
    stimuli = {}
    running = True
    font = pygame.font.SysFont(None, 36)
    
    print("🎮 Ani Void Reflex Subsystem Live!")
    print("Keys: N=Sudden Noise, T=Touch, H=Happy Cue, S=Scared Cue, Q=Quit")
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_n: stimuli = {"sudden_noise": True}
                elif event.key == pygame.K_t: stimuli = {"touch": True}
                elif event.key == pygame.K_h: stimuli = {"emotional_cue": "happy"}
                elif event.key == pygame.K_s: stimuli = {"emotional_cue": "scared"}
        
        ani.update(stimuli)
        stimuli = {}
        
        screen.fill(BLACK)
        ani.draw(screen)
        
        emotion_text = font.render(f"Emotion: {ani.emotion.upper()}", True, CYAN)
        screen.blit(emotion_text, (10, 10))
        
        pygame.display.flip()
        clock.tick(30)
    
    pygame.quit()

if __name__ == "__main__":
    main()