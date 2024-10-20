from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import logging
from core.ui.base import UIBase, UIClosedError, UserInput
from core.state.state_manager import StateManager
from core.db.session import SessionManager
from argparse import Namespace
from core.cli.helpers import load_project, delete_project, show_config
from core.agents.orchestrator import Orchestrator
from core.config import get_config
from core.llm.base import APIError, BaseLLMClient

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "http://localhost:5174"]}})

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.after_request
def after_request(response):
    logger.debug(f"Response headers: {dict(response.headers)}")
    return response

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


class WebUI(UIBase):
    def __init__(self):
        self.output = ""

    async def start(self) -> bool:
        return True

    async def stop(self):
        pass

    async def send_message(self, message: str, **kwargs):
        self.output += message + "\n"

    async def ask_question(self, question: str, **kwargs) -> UserInput:
        self.output += question + "\n"
        return UserInput(button=None, text="")

@app.route('/api/start_project', methods=['POST'])
def start_project():
    try:
        project_name = request.json['name']
        logger.info(f"Starting new project: {project_name}")
        ui = WebUI()
        db = SessionManager()
        sm = StateManager(db, ui)

        async def create_project():
            return await sm.create_project(project_name)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        project_state = loop.run_until_complete(create_project())

        if project_state:
            logger.info(f"Project created successfully: {project_name}")
            return jsonify({"output": ui.output or f"Project '{project_name}' created successfully"})
        else:
            logger.error(f"Failed to create project: {project_name}")
            return jsonify({"error": f"Failed to create project '{project_name}'"}), 400
    except Exception as e:
        logger.exception(f"Error while creating project: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/list_projects', methods=['GET'])
def list_projects():
    try:
        logger.info("Listing projects")
        db = SessionManager()
        sm = StateManager(db)
        
        async def get_projects():
            return await sm.list_projects()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        projects = loop.run_until_complete(get_projects())
        
        logger.info(f"Found {len(projects)} projects")
        return jsonify({"projects": [{"id": str(p.id), "name": p.name} for p in projects]})
    except Exception as e:
        logger.exception(f"Error while listing projects: {str(e)}")
        return jsonify({"error": f"An error occurred while listing projects: {str(e)}"}), 500

@app.route('/api/run_project', methods=['POST'])
def run_project():
    try:
        project_id = request.json['id']
        logger.info(f"Running project with ID: {project_id}")
        ui = WebUI()
        db = SessionManager()
        sm = StateManager(db, ui)
        args = Namespace(project=project_id, branch=None, step=None)

        async def run():
            success = await load_project(sm, args.project, args.branch, args.step)
            if not success:
                logger.error(f"Failed to load project: {project_id}")
                return False

            orca = Orchestrator(sm, ui)
            try:
                success = await orca.run()
            except (KeyboardInterrupt, UIClosedError):
                logger.warning("Project execution interrupted")
                await sm.rollback()
            except Exception as err:
                logger.exception(f"Error during project execution: {str(err)}")
                await sm.rollback()
                ui.output += f"Error: {str(err)}\n"

            return success

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(run())

        if success:
            logger.info(f"Project ran successfully: {project_id}")
            return jsonify({"output": ui.output or f"Project '{project_id}' ran successfully"})
        else:
            logger.error(f"Failed to run project: {project_id}")
            return jsonify({"error": f"Failed to run project '{project_id}'"}), 400
    except Exception as e:
        logger.exception(f"Error while running project: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/delete_project/<uuid:project_id>', methods=['DELETE'])
def delete_project_route(project_id):
    try:
        logger.info(f"Deleting project with ID: {project_id}")
        db = SessionManager()
        
        async def delete():
            return await delete_project(db, project_id)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(delete())

        if success:
            logger.info(f"Project deleted successfully: {project_id}")
            return jsonify({"output": f"Project '{project_id}' deleted successfully"})
        else:
            logger.error(f"Failed to delete project: {project_id}")
            return jsonify({"error": f"Failed to delete project '{project_id}'"}), 400
    except Exception as e:
        logger.exception(f"Error while deleting project: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/show_config', methods=['GET'])
def show_config_route():
    try:
        logger.info("Fetching configuration")
        config = get_config()
        return jsonify(config.model_dump())
    except Exception as e:
        logger.exception(f"Error while fetching configuration: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
