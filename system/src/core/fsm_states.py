from aiogram.fsm.state import State, StatesGroup

class FormState(StatesGroup):
    """
    Finite State Machine (FSM) definitions.
    Determines what the user is currently doing.
    """
    
    # 1. Entry Point
    main_menu = State()

    # 2. Parser Workflow
    awaiting_topic = State()       # Waiting for user to pick a topic
    
    # 3. Post Interaction (The main loop)
    viewing_post = State()         # User is looking at a post card
    
    # 4. Forwarding Workflow
    awaiting_forwarded_post = State() # Waiting for user to forward a message
    
    # 5. Manual Editing / Input
    awaiting_text_input = State()    # Editing post text manually
    awaiting_media_input = State()   # Uploading custom photo/video
    awaiting_prompt_input = State()  # Entering Stable Diffusion prompt
    
    # 6. Navigation
    awaiting_post_jump = State()     # Waiting for page number input (1-100)
    
    # 7. Background / Processing
    generating_image = State()       # Image generation in progress